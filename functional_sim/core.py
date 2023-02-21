from regfile import RegisterFile, Reg
from util import BitVec


class executor:
    EXEC_FUNC = {}  # Populated by @exec decorator

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

    def __init__(self, imem, sdmem, vdmem):
        self.IMEM = imem
        self.SDMEM = sdmem
        self.VDMEM = vdmem

        self.SRF = RegisterFile(Reg.SCALAR, 8)
        self.VRF = RegisterFile(Reg.VECTOR, 8, Core.MVL)

        # Initialize special registers
        self.PC = 0
        self.VL = Core.MVL
        self.VM = [1 for i in range(Core.MVL)]

        self.halted = False
        # For branching
        self.branch_taken = False
        self.branch_PC = 0

    def run(self):
        count = 0
        while not self.halted:
            self.branch_taken = False

            ins = self.IMEM.Read(self.PC)
            print(f"INS {count:>5}: {self.PC:<8} {ins}")
            ex = executor.get(ins.opcode)
            ex(self, ins)

            if self.branch_taken:
                self.PC = self.branch_PC
            else:
                self.PC = self.PC + 1
            count += 1

    @executor("ADD", "SUB", "AND", "OR", "XOR", "SLL", "SRL", "SRA")
    def exec_arithmetic_scalar(self, ins):
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
        self.VRF.Write(ins.dst(), res, self.VM, self.VL)

    @executor("ADDVS", "SUBVS", "MULVS", "DIVVS")
    def exec_arithmetic_vector_scalar(self, ins):
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
        self.VRF.Write(ins.dst(), res, mask=self.VM, length=self.VL)

    def get_mem_addresses(self, ins):
        start_addr = self.SRF.Read(ins.src(0)).unsigned()
        if ins.opcode[2:] == "WS":
            # Stride SR
            stride = self.SRF.Read(ins.src(1)).unsigned()
            addrs = list(range(start_addr, start_addr + Core.MVL*stride, stride))
        if ins.opcode[2:] == "I":
            # Strides taken from VR
            strides = self.VRF.Read(ins.src(1)).unsigned()
            addrs = [start_addr + s.unsigned for s in strides]
        else:
            # Stride 1
            addrs = list(range(start_addr, start_addr + Core.MVL))
        return addrs

    @executor("LV", "LVWS", "LVI")
    def exec_load_vector(self, ins):
        addrs = self.get_mem_addresses(ins)
        res = [None] * Core.MVL
        for i in range(self.VL):
            # Check vector mask
            if self.VM[i]:
                res[i] = self.VDMEM.Read(addrs[i])
        self.VRF.Write(ins.dst(), res, mask=self.VM, length=self.VL)

    @executor("SV", "SVWS", "SVI")
    def exec_store_vector(self, ins):
        addrs = self.get_mem_addresses(ins)
        res = self.VRF.Read(ins.dst())
        for i in range(self.VL):
            # Check vector mask
            if self.VM[i]:
                self.VDMEM.Write(addrs[i], res[i])

    @executor("BEQ", "BNE", "BGT", "BLT", "BGE", "BLE")
    def exec_branch(self, ins):
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
        self.branch_taken = taken
        self.branch_PC = self.PC + offset

    @executor("CVM")
    def exec_cvm(self, ins):
        for i in range(Core.MVL):
            self.VM[i] = 1

    @executor("POP")
    def exec_pop(self, ins):
        count = BitVec(sum(self.VM))
        self.SRF.Write(ins.dst(), count)

    @executor("MTCL")
    def exec_mtcl(self, ins):
        reg = self.SRF.Read(ins.op(0))
        self.VL = reg.unsigned()

    @executor("MFCL")
    def exec_mfcl(self, ins):
        reg = BitVec(self.VL)
        self.SRF.Write(ins.op(0), reg)

    @executor("HALT")
    def exec_halt(self, ins):
        self.halted = True

    @executor("LS")
    def exec_load_scalar(self, ins):
        addr = self.SRF.Read(ins.src(0)).unsigned() + ins.imm()
        val = self.SDMEM.Read(addr)
        self.SRF.Write(ins.dst(), val)

    @executor("SS")
    def exec_store_scalar(self, ins):
        addr = self.SRF.Read(ins.src(0)).unsigned() + ins.imm()
        val = self.SRF.Read(ins.dst())
        self.SDMEM.Write(addr, val)

    def dumpregs(self, iodir):
        self.SRF.dump(iodir)
        self.VRF.dump(iodir)
