import os
from collections import deque
from math import ceil

from itrace import Reg

VEC_DATA_OPS = {"LV", "LVWS", "LVI", "SV", "SVWS", "SVI"}
VEC_COMPUTE_OPS = {"ADDVS", "SUBVS", "MULVS", "DIVVS", "ADDVV", "SUBVV", "MULVV", "DIVVV", "SEQVV", "SNEVV", "SGTVV", "SLTVV", "SGEVV", "SLEVV", "SEQVS", "SNEVS", "SGTVS", "SLTVS", "SGEVS", "SLEVS"}
VEC_MASK_OPS = {"SEQVV", "SNEVV", "SGTVV", "SLTVV", "SGEVV", "SLEVV", "SEQVS", "SNEVS", "SGTVS", "SLTVS", "SGEVS", "SLEVS"}
VEC_OPS = VEC_DATA_OPS | VEC_COMPUTE_OPS
VMR_SCALAR_OPS = {"CVM", "POP"}
VLR_SCALAR_OPS = {"MTCL", "MFCL"}
SCALAR_DST_OPS = {"ADD", "SUB", "AND", "OR", "XOR", "LS", "SLL", "SRL", "SRA", "MFCL", "POP"}
BRANCH_OPS = {"BGT", "BGE", "BLE", "BLT", "BEQ", "BNE"}

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

    def __init__(self, itrace, config, iodir, cyclewise=False):
        self.ITrace = itrace
        self.config = config
        if cyclewise:
            self.cyclewise = open(os.path.join(iodir, "cyclewise.log"), "w")
        else:
            self.cyclewise = None



        # Dynamic ins counter
        self.count = 0
        self.cycle = 0
        self.halted = False

        # Decode BusyBoard, True means free, False means busy
        # 8 registers + VMR, VLR for SRF
        self.srf_busyboard = [True for _ in range(10)]
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
        # Load-store pipeline
        banks = self.config.vdmNumBanks
        bankwait = self.config.vdmBankWait
        lanes = self.config.numLanes

        self.addr_queues = None
        self.lane_pipes = [[None for _ in range(self.config.vlsPipelineDepth)] for _ in range(lanes)]
        self.bank_busyboard = [True for _ in range(banks)]
        self.addrs_remaining = 0

        # Backend compute
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
        if self.cyclewise:
            print(*args, file=self.cyclewise)

    def run(self):
        stop = False
        while not stop:
            self.logcycle("===== cycle", self.cycle)
            self.backend_stage()

            # Try all three but only do one per cycle
            # Arbitration priority is fixed, first data, then compute, then scalar
            if not self.dispatch_vec_data():
                if not self.dispatch_vec_compute():
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

        if self.cyclewise:
            self.cyclewise.close()

        return self.cycle

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

        if ins.opcode in VMR_SCALAR_OPS or ins.opcode in VEC_OPS:
            free = free and self.srf_busyboard[8]
        if ins.opcode in VLR_SCALAR_OPS or ins.opcode in VEC_OPS:
            free = free and self.srf_busyboard[9]
        return free

    def mark_busyboard(self, ins):
        # Mark instruction operands as busy
        for op in ins.ops:
            if type(op) is not Reg:
                continue
            if op.ty == Reg.VECTOR:
                self.vrf_busyboard[op.idx] = False
            # Scalar reg checked below only for destination
        if ins.opcode == 'CVM' or ins.opcode in VEC_MASK_OPS:
            # Writes to VMR
            self.srf_busyboard[8] = False
        if ins.opcode == 'MTCL':
            # Writes to VLR
            self.srf_busyboard[9] = False
        if ins.opcode in SCALAR_DST_OPS:
            # Only destination scalar regs are marked busy.
            # Source regs are passed along with the ins at decode
            # so no need to mark busy.
            self.srf_busyboard[ins.op(0).idx] = False

    def unmark_busyboard(self, ins):
        # Mark instruction operands as free
        for op in ins.ops:
            if type(op) is not Reg:
                continue
            if op.ty == Reg.VECTOR:
                self.vrf_busyboard[op.idx] = True
        if ins.opcode == 'CVM' or ins.opcode in VEC_MASK_OPS:
            # VMR
            self.srf_busyboard[8] = True
        if ins.opcode == 'MTCL':
            # VLR
            self.srf_busyboard[9] = True
        if ins.opcode in SCALAR_DST_OPS:
            self.srf_busyboard[ins.op(0).idx] = True


    def decode_stage(self):
        if self.decode_free:
            return

        ins = self.decode_ins
        self.logcycle("  decode:", ins)
        if ins.opcode not in BRANCH_OPS and not self.check_busyboard(ins):
            # Wait for instruction ops to be free
            # Do not check for branch as they are already resolved
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
            if len(self.vec_compute_q) < self.config.computeQueueDepth:
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


    def dispatch_vec_data(self):
        if len(self.vec_data_q) == 0:
            return False
        vmem_ins = self.vec_data_q[0]
        self.logcycle("  dispatch vmem:", vmem_ins)
        if self.mem_free:
            self.mem_ins = vmem_ins
            self.mem_free = False
            self.vec_data_q.popleft()

            if vmem_ins.value is None:
                raise Exception(f"Memory instruction {vmem_ins} does not have addresses")
            if type(vmem_ins.value) is not list:
                addrs = [vmem_ins.value]
            else:
                addrs = vmem_ins.value

            lanes = self.config.numLanes
            self.addr_queues = [deque(addrs[i::lanes]) for i in range(lanes)]
            self.addrs_remaining = len(addrs)
            for i in range(lanes):
                if len(self.addr_queues[i]) > 0:
                    self.lane_pipes[i][0] = self.addr_queues[i].popleft()

            return True
        return False

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
            return False
        vcomp_ins = self.vec_compute_q[0]
        self.logcycle("  dispatch vcomp:", vcomp_ins)
        if vcomp_ins.opcode.startswith("MUL"):
            if self.mul_free:
                self.mul_ins = vcomp_ins
                self.mul_free = False
                self.mul_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()
                return True
        elif vcomp_ins.opcode.startswith("DIV"):
            if self.div_free:
                self.div_ins = vcomp_ins
                self.div_free = False
                self.div_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()
                return True
        else:
            if self.add_free:
                self.add_ins = vcomp_ins
                self.add_free = False
                self.add_cycles_left = self.get_compute_cycles(vcomp_ins)
                self.vec_compute_q.popleft()
                return True
        return False

    def dispatch_scalar(self):
        if not self.dispatch_scalar_free:
            if self.scalar_free:
                self.scalar_ins = self.dispatch_scalar_ins
                self.logcycle("  dispatch scalar:", self.scalar_ins)
                self.scalar_free = False
                self.dispatch_scalar_ins = None
                self.dispatch_scalar_free = True
                return True
        return False

    def backend_mem(self):
        if self.addrs_remaining == 0:
            return 

        banks = self.config.vdmNumBanks
        bankwait = self.config.vdmBankWait
        pdepth = self.config.vlsPipelineDepth
        lanes = self.config.numLanes

        def get_bank(addr):
            return addr % banks

        addr_queues = self.addr_queues
        lane_pipes = self.lane_pipes
        bank_busyboard = self.bank_busyboard

        # Simulate the load-store pipeline
            # Advance lane pipelines
        for i in range(lanes):
            self.logcycle("    backend mem queue:", lane_pipes[i])
            # Bank access wait is over, free the busyboard 
            if lane_pipes[i][bankwait] is not None:
                bank_busyboard[get_bank(lane_pipes[i][bankwait])] = True

            # Addr processed
            if lane_pipes[i][-1] is not None:
                self.addrs_remaining -= 1

            for j in range(pdepth-2):
                lane_pipes[i][pdepth-1-j] = lane_pipes[i][pdepth-2-j]
            # 0th can advance only if not stalled
            addr = lane_pipes[i][0]
            if addr is not None and bank_busyboard[get_bank(addr)]:
                lane_pipes[i][1] = addr
                lane_pipes[i][0] = None
                bank_busyboard[get_bank(addr)] = False
            else:
                # Insert stall
                lane_pipes[i][1] = None
            # Push new addrs
            if lane_pipes[i][0] is None and len(addr_queues[i]) > 0:
                lane_pipes[i][0] = addr_queues[i].popleft()

    def backend_stage(self):
        if not self.mem_free:
            self.logcycle("  backend mem:", self.mem_ins)
            self.backend_mem()
            if self.addrs_remaining == 0:
                self.unmark_busyboard(self.mem_ins)
                self.mem_ins = None
                self.mem_free = True

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

