import os

from regfile import RegisterFile, Reg
from bitvec import BitVec


class executor:
    # The @executor decorator registers the decorated function
    # as executor of the listed instruction opcodes.
    # The EXEC_FUNC map is populated as opcode: exec function pairs.
    EXEC_FUNC = {}

    def __init__(self, *opcodes):
        self.opcodes = opcodes

    def __call__(self, func):
        for op in self.opcodes:
            executor.EXEC_FUNC[op] = func

    @classmethod
    def get(cls, opcode):
        if opcode not in cls.EXEC_FUNC:
            raise NotImplementedError(f"Opcode {opcode} not registered")
        return cls.EXEC_FUNC[opcode]


class Core:
    MVL = 64  # Max vector length

    def __init__(self, imem, sdmem, vdmem, trace=False):
        self.IMEM = imem
        self.SDMEM = sdmem
        self.VDMEM = vdmem

        self.SRF = RegisterFile(Reg.SCALAR, 8)
        self.VRF = RegisterFile(Reg.VECTOR, 8, Core.MVL)

        # Initialize special registers
        self.PC = 0
        self.VL = Core.MVL # Vector Length
        self.VM = [1 for i in range(Core.MVL)] # Vector Mask 0/1

        self.halted = False
        # For branching
        self.branch_taken = False
        self.branch_PC = 0

        # Dynamic instruction trace
        if trace:
            self.trace = []
        else:
            self.trace = None

    def run(self):
        count = 0 # Dynamic instruction count
        while not self.halted:
            # Set to false here, if branch is taken, execution will set to True
            self.branch_taken = False

            # Read instruction from memory
            ins = self.IMEM.Read(self.PC)
            if self.trace is not None:
                self.trace.append([ins, None])
            # print(f"INS {count:>5}: {self.PC:<8} {ins}")
            # Lookup executor based on opcode
            ex = executor.get(ins.opcode)
            # Execute the instruction
            ex(self, ins)

            # Update PC to branch target or PC+1
            if self.branch_taken:
                self.PC = self.branch_PC
            else:
                self.PC = self.PC + 1

            count += 1 # Increment dynamic count

    # Append runtime value to trace
    def trace_value(self, value):
        if self.trace is not None:
            self.trace[-1][1] = value

    @executor("ADD", "SUB", "AND", "OR", "XOR", "SLL", "SRL", "SRA")
    def exec_arithmetic_scalar(self, ins):
        # Scalar arithmetic instructions
        a = self.SRF.Read(ins.src(0))
        b = self.SRF.Read(ins.src(1))
        if ins.opcode == "ADD":
            res = BitVec.add(a, b)
        elif ins.opcode == "SUB":
            res = BitVec.sub(a, b)
        elif ins.opcode == "AND":
            res = BitVec.bitand(a, b)
        elif ins.opcode == "OR":
            res = BitVec.bitor(a, b)
        elif ins.opcode == "XOR":
            res = BitVec.bitxor(a, b)
        elif ins.opcode == "SLL":
            res = BitVec.sll(a, b)
        elif ins.opcode == "SRL":
            res = BitVec.srl(a, b)
        elif ins.opcode == "SRA":
            res = BitVec.sra(a, b)
        else:
            raise NotImplementedError(f"Opcode not supported in exec_arithmetic_scalar: {ins.opcode}")
        self.SRF.Write(ins.dst(), res)

    @executor("ADDVV", "SUBVV", "MULVV", "DIVVV")
    def exec_arithmetic_vector_vector(self, ins):
        # Vector-Vector arithmetic instructions
        veca = self.VRF.Read(ins.src(0))
        vecb = self.VRF.Read(ins.src(1))
        res = [None]*Core.MVL
        for i in range(self.VL):
            # Check vector mask
            if not self.VM[i]:
                continue

            if ins.opcode == "ADDVV":
                res[i] = BitVec.add(veca[i], vecb[i])
            elif ins.opcode == "SUBVV":
                res[i] = BitVec.sub(veca[i], vecb[i])
            elif ins.opcode == "MULVV":
                res[i] = BitVec.mul(veca[i], vecb[i])
            elif ins.opcode == "DIVVV":
                res[i] = BitVec.div(veca[i], vecb[i])
            else:
                raise NotImplementedError(f"Opcode not supported in exec_arith_vv: {ins.opcode}")
        self.trace_value(self.VL)
        self.VRF.Write(ins.dst(), res, self.VM, self.VL)

    @executor("ADDVS", "SUBVS", "MULVS", "DIVVS")
    def exec_arithmetic_vector_scalar(self, ins):
        # Vector-Scalar arithmetic instructions
        veca = self.VRF.Read(ins.src(0))
        b = self.SRF.Read(ins.src(1))
        res = [None] * Core.MVL
        for i in range(self.VL):
            # Check vector mask
            if not self.VM[i]:
                continue

            if ins.opcode == "ADDVS":
                res[i] = BitVec.add(veca[i], b)
            elif ins.opcode == "SUBVS":
                res[i] = BitVec.sub(veca[i], b)
            elif ins.opcode == "MULVS":
                res[i] = BitVec.mul(veca[i], b)
            elif ins.opcode == "DIVVS":
                res[i] = BitVec.div(veca[i], b)
            else:
                raise NotImplementedError(f"Opcode not supported in exec_arith_vv: {ins.opcode}")
        self.trace_value(self.VL)
        self.VRF.Write(ins.dst(), res, mask=self.VM, length=self.VL)

    def get_mem_addresses(self, ins):
        # Generate addresses for vector load and store instructions
        # based on type of access (direct, strided, scatter/gather)
        start_addr = self.SRF.Read(ins.src(0)).unsigned()
        if ins.opcode[2:] == "WS":
            # Stride SR
            stride = self.SRF.Read(ins.src(1)).unsigned()
            if stride > 0:
                addrs = list(range(start_addr, start_addr + Core.MVL*stride, stride))
            else:
                addrs = [start_addr] * Core.MVL
        elif ins.opcode[2:] == "I":
            # Offsets taken from VR
            offsets = self.VRF.Read(ins.src(1))
            addrs = [start_addr + s.unsigned() for s in offsets]
        else:
            # Stride 1
            addrs = list(range(start_addr, start_addr + Core.MVL))
        # print(f"    Addresses: {addrs}")
        return addrs

    @executor("LV", "LVWS", "LVI")
    def exec_load_vector(self, ins):
        # Load vector (with stride, gather)
        addrs = self.get_mem_addresses(ins)
        res = [None] * Core.MVL
        for i in range(self.VL):
            # Check vector mask
            if self.VM[i]:
                res[i] = self.VDMEM.Read(addrs[i])
        self.VRF.Write(ins.dst(), res, mask=self.VM, length=self.VL)
        self.trace_value(addrs[:self.VL])

    @executor("SV", "SVWS", "SVI")
    def exec_store_vector(self, ins):
        # Store vector (with sttride, scatter)
        addrs = self.get_mem_addresses(ins)
        res = self.VRF.Read(ins.dst())
        for i in range(self.VL):
            # Check vector mask
            if self.VM[i]:
                self.VDMEM.Write(addrs[i], res[i])
        self.trace_value(addrs[:self.VL])

    @executor("BEQ", "BNE", "BGT", "BLT", "BGE", "BLE")
    def exec_branch(self, ins):
        # Branch instruction
        a = self.SRF.Read(ins.op(0))
        b = self.SRF.Read(ins.op(1))
        offset = ins.imm()
        taken = False
        if ins.opcode == "BEQ":
            taken = a.signed() == b.signed()
        elif ins.opcode == "BNE":
            taken = a.signed() != b.signed()
        elif ins.opcode == "BGT":
            taken = a.signed() > b.signed()
        elif ins.opcode == "BLT":
            taken = a.signed() < b.signed()
        elif ins.opcode == "BGE":
            taken = a.signed() >= b.signed()
        elif ins.opcode == "BLE":
            taken = a.signed() <= b.signed()
        else:
            raise NotImplementedError(f"Opcode not supported in exec_branch: {ins.opcode}")
        # Set the global signal for branch taken, so execution loop updates
        # PC to branch target
        self.branch_taken = taken
        self.branch_PC = self.PC + offset
        self.trace_value(self.branch_PC if taken else (self.PC + 1))

    @executor("CVM")
    def exec_cvm(self, ins):
        # Clear vector mask
        for i in range(Core.MVL):
            self.VM[i] = 1

    @executor("POP")
    def exec_pop(self, ins):
        # Pop vector mask count to reg
        count = BitVec(sum(self.VM))
        self.SRF.Write(ins.dst(), count)

    @executor("MTCL")
    def exec_mtcl(self, ins):
        # Move to vector length
        reg = self.SRF.Read(ins.op(0))
        self.VL = reg.unsigned()

    @executor("MFCL")
    def exec_mfcl(self, ins):
        # Move from vector length
        reg = BitVec(self.VL)
        self.SRF.Write(ins.op(0), reg)

    @executor("HALT")
    def exec_halt(self, ins):
        # Halt execution
        self.halted = True

    @executor("LS")
    def exec_load_scalar(self, ins):
        # Load scalar
        addr = self.SRF.Read(ins.src(0)).unsigned() + ins.imm()
        val = self.SDMEM.Read(addr)
        self.SRF.Write(ins.dst(), val)
        self.trace_value(addr)

    @executor("SS")
    def exec_store_scalar(self, ins):
        # Store scalar
        addr = self.SRF.Read(ins.src(0)).unsigned() + ins.imm()
        val = self.SRF.Read(ins.dst())
        self.SDMEM.Write(addr, val)
        self.trace_value(addr)
        
    @executor("SEQVV", "SNEVV", "SGTVV", "SLTVV", "SGEVV", "SLEVV")
    def exec_svv(self, ins):
        veca = self.VRF.Read(ins.op(0))
        vecb = self.VRF.Read(ins.op(1))
        if ins.opcode == "SEQVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() == vecb[i].signed() else 0
        elif ins.opcode == "SNEVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() != vecb[i].signed() else 0
        elif ins.opcode == "SGTVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() > vecb[i].signed() else 0
        elif ins.opcode == "SLTVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() < vecb[i].signed() else 0
        elif ins.opcode == "SGEVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() >= vecb[i].signed() else 0
        elif ins.opcode == "SLEVV":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() <= vecb[i].signed() else 0
        else:
            raise NotImplementedError(f"Opcode not supported in exec_svv: {ins.opcode}")

    @executor("SEQVS", "SNEVS", "SGTVS", "SLTVS", "SGEVS", "SLEVS")
    def exec_svs(self, ins):
        veca = self.VRF.Read(ins.op(0))
        b = self.SRF.Read(ins.op(1))
        if ins.opcode == "SEQVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() == b.signed() else 0
        elif ins.opcode == "SNEVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() != b.signed() else 0
        elif ins.opcode == "SGTVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() > b.signed() else 0
        elif ins.opcode == "SLTVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() < b.signed() else 0
        elif ins.opcode == "SGEVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() >= b.signed() else 0
        elif ins.opcode == "SLEVS":
            for i in range(Core.MVL):
                self.VM[i] = 1 if veca[i].signed() <= b.signed() else 0
        else:
            raise NotImplementedError(f"Opcode not supported in exec_svs: {ins.opcode}")        

    def dumpregs(self, iodir):
        self.SRF.dump(iodir)
        self.VRF.dump(iodir)

    def dumptrace(self, iodir):
        if self.trace is None:
            return

        opfilepath = os.path.abspath(os.path.join(iodir, "trace.txt"))
        with open(opfilepath, "w") as opf:
            for dynins, value in self.trace:
                ops = " ".join(str(o) for o in dynins.ops)
                if value is not None:
                    if type(value) is list:
                        value = ",".join(str(v) for v in value)
                    opf.write(f"{dynins.opcode} {ops} ({value})\n")
                else:
                    opf.write(f"{dynins.opcode} {ops}\n")
