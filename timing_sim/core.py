import os
from collections import deque
from math import ceil

from itrace import Reg

VEC_DATA_OPS = {"LV", "LVWS", "LVI", "SV", "SVWS", "SVI"}
VEC_COMPUTE_OPS = {"ADDVS", "SUBVS", "MULVS", "DIVVS", "ADDVV", "SUBVV", "MULVV", "DIVVV", "SEQVV", "SNEVV", "SGTVV", "SLTVV", "SGEVV", "SLEVV", "SEQVS", "SNEVS", "SGTVS", "SLTVS", "SGEVS", "SLEVS"}

class Config(dict):
    def __init__(self, iodir):
        self.filepath = os.path.abspath(os.path.join(iodir, "Config.txt"))
        self.parameters = {} # dictionary of parameter name: value as strings.

        try:
            with open(self.filepath, 'r') as conf:
                for line in conf:
                    if '#' in line:
                        line = line[:line.index('#')]
                    if line.strip() == '':
                        continue
                    key, val = line.split('=')
                    key, val = key.strip(), val.strip()
                    self.parameters[key] = int(val)
                    setattr(self, key, int(val))
            print("Config - Parameters loaded from file:", self.filepath)
            print("Config parameters:", self.parameters)
        except:
            print("Config - ERROR: Couldn't open file in path:", self.filepath)
            raise

class Core:
    MVL = 64  # Max vector length

    def __init__(self, itrace, config):
        self.ITrace = itrace
        self.config = config

        # Dynamic ins counter
        self.count = 0
        self.cycle = 0
        self.halted = False

        # Decode BusyBoard, True means free, False means busy
        self.srf_busyboard = [True for _ in range(8)]
        self.vrf_busyboard = [True for _ in range(8)]

        # Fetch to Decode 
        self.decode_ins = None
        self.decode_free = True

        # Dispatch queues
        self.vec_data_q = deque()
        self.vec_compute_q = deque()
        self.dispatch_scalar_ins = None
        self.dispatch_scalar_free = True

        # Dispatch to Backend
        self.mem_ins = None
        self.mem_free = True
        self.mem_cycles_left = 0
        self.mul_ins = None
        self.mul_free = True
        self.mul_cycles_left = 0
        self.div_ins = None
        self.div_free = True
        self.div_cycles_left = 0
        self.add_ins = None
        self.add_free = True
        self.add_cycles_left = 0
        self.scalar_ins = None
        self.scalar_free = True

    def logcycle(self, *args):
        print(*args)

    def run(self):
        stop = False
        while not stop:
            self.logcycle("===== cycle", self.cycle)
            self.backend_stage()

            self.dispatch_vec_data()
            self.dispatch_vec_compute()
            self.dispatch_scalar()

            self.decode_stage()

            self.fetch_stage()

            # Increment cycle
            self.cycle += 1

            # Check if all stages are empty
            stop = self.halted and self.mul_free and self.div_free and self.add_free \
                    and self.scalar_free and self.mem_free and self.dispatch_scalar_free \
                    and (len(self.vec_data_q) == 0) and (len(self.vec_compute_q) == 0) \
                    and self.decode_free

    def fetch_stage(self):
        if self.decode_free and not self.halted:
            # Read instruction from trace, and pass it to decode
            self.decode_ins = self.ITrace.Read(self.count)
            self.decode_free = False
            self.count += 1 
            self.logcycle("  fetch:", self.decode_ins)
            if self.decode_ins.opcode == "HALT":
                self.halted = True

    def check_busyboard(self, ins):
        # Check if instruction operands are free in the busyboard
        free = True
        for op in ins.ops:
            if type(op) is not Reg:
                continue
            free = free and (((op.ty == Reg.SCALAR) and self.srf_busyboard[op.idx])
                    or ((op.ty == Reg.VECTOR) and self.vrf_busyboard[op.idx]))
        return free

    def mark_busyboard(self, ins):
        # Mark instruction operands as busy
        for op in ins.ops:
            if type(op) is not Reg:
                continue
            if op.ty == Reg.SCALAR:
                self.srf_busyboard[op.idx] = False
            elif op.ty == Reg.VECTOR:
                self.vrf_busyboard[op.idx] = False

    def unmark_busyboard(self, ins):
        # Mark instruction operands as free
        for op in ins.ops:
            if type(op) is not Reg:
                continue
            if op.ty == Reg.SCALAR:
                self.srf_busyboard[op.idx] = True
            elif op.ty == Reg.VECTOR:
                self.vrf_busyboard[op.idx] = True


    def decode_stage(self):
        if self.decode_free:
            return

        ins = self.decode_ins
        self.logcycle("  decode:", ins)
        if not self.check_busyboard(ins):
            # Wait for instruction ops to be free
            return

        if ins.opcode in VEC_DATA_OPS:
            if len(self.vec_data_q) < self.config.dataQueueDepth:
                # Pass on instruction to dispatch
                self.vec_data_q.append(self.decode_ins)
                # Free input of decode
                self.decode_ins = None
                self.decode_free = True
                self.mark_busyboard(ins)
        elif ins.opcode in VEC_COMPUTE_OPS:
            if len(self.vec_data_q) < self.config.computeQueueDepth:
                # Pass on instruction to dispatch
                self.vec_compute_q.append(self.decode_ins)
                # Free input of decode
                self.decode_ins = None
                self.decode_free = True
                self.mark_busyboard(ins)
        else:
            if self.dispatch_scalar_free:
                self.dispatch_scalar_ins = ins
                self.dispatch_scalar_free = False
                # Free input of decode
                self.decode_ins = None
                self.decode_free = True
                self.mark_busyboard(ins)

    def get_mem_cycles(self, ins):
        banks = self.config.vdmNumBanks
        pdepth = self.config.vlsPipelineDepth
        if ins.value is None:
            raise Exception(f"Memory instruction {ins} does not have addresses")
        if type(ins.value) is not list:
            addrs = [ins.value]
        else:
            addrs = ins.value
        perbank = [0 for _ in range(banks)]
        for addr in addrs:
            perbank[addr % banks] += 1
        maxperbank = max(perbank)
        return pdepth - 1 + maxperbank

    def dispatch_vec_data(self):
        if len(self.vec_data_q) == 0:
            return
        vmem_ins = self.vec_data_q[0]
        self.logcycle("  dispatch vmem:", vmem_ins)
        if self.mem_free:
            self.mem_ins = vmem_ins
            self.mem_free = False
            self.mem_cycles_left = self.get_mem_cycles(vmem_ins)
            self.vec_data_q.popleft()

    def get_compute_cycles(self, ins):
        lanes = self.config.numLanes
        if ins.opcode.startswith("MUL"):
            pdepth = self.config.pipelineDepthMul
        elif ins.opcode.startswith("DIV"):
            pdepth = self.config.pipelineDepthDiv
        else:
            pdepth = self.config.pipelineDepthAdd
        veclen = ins.value if ins.value is not None else Core.MVL
        return pdepth - 1 + ceil(veclen / lanes)

    def dispatch_vec_compute(self):
        pMul = self.config.pipelineDepthMul
        pDiv = self.config.pipelineDepthDiv
        pAdd = self.config.pipelineDepthAdd

        if len(self.vec_compute_q) == 0:
            return
        vcomp_ins = self.vec_compute_q[0]
        self.logcycle("  dispatch vcomp:", vcomp_ins)
        if vcomp_ins.opcode.startswith("MUL"):
            if self.mul_free:
                self.mul_ins = vcomp_ins
                self.mul_free = False
                self.mul_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()
        elif vcomp_ins.opcode.startswith("DIV"):
            if self.div_free:
                self.div_ins = vcomp_ins
                self.div_free = False
                self.div_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()
        else:
            if self.add_free:
                self.add_ins = vcomp_ins
                self.add_free = False
                self.add_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()

    def dispatch_scalar(self):
        if not self.dispatch_scalar_free:
            if self.scalar_free:
                self.scalar_ins = self.dispatch_scalar_ins
                self.logcycle("  dispatch scalar:", self.scalar_ins)
                self.scalar_free = False
                self.dispatch_scalar_ins = None
                self.dispatch_scalar_free = True

    def backend_stage(self):
        if not self.mem_free:
            self.logcycle("  backend mem:", self.mem_ins, "cycles", self.mem_cycles_left)
            if self.mem_cycles_left == 1:
                self.unmark_busyboard(self.mem_ins)
                self.mem_ins = None
                self.mem_free = True
            else:
                self.mem_cycles_left -= 1

        if not self.mul_free:
            self.logcycle("  backend mul:", self.mul_ins, "cycles", self.mul_cycles_left)
            if self.mul_cycles_left == 1:
                self.unmark_busyboard(self.mul_ins)
                self.mul_ins = None
                self.mul_free = True
            else:
                self.mul_cycles_left -= 1

        if not self.div_free:
            self.logcycle("  backend div:", self.div_ins, "cycles", self.div_cycles_left)
            if self.div_cycles_left == 1:
                self.unmark_busyboard(self.div_ins)
                self.div_ins = None
                self.div_free = True
            else:
                self.div_cycles_left -= 1

        if not self.add_free:
            self.logcycle("  backend add:", self.add_ins, "cycles", self.add_cycles_left)
            if self.add_cycles_left == 1:
                self.unmark_busyboard(self.add_ins)
                self.add_ins = None
                self.add_free = True
            else:
                self.add_cycles_left -= 1

        if not self.scalar_free:
            self.logcycle("  backend scalar:", self.scalar_ins)
            self.unmark_busyboard(self.scalar_ins)
            self.scalar_ins = None
            self.scalar_free = True
