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

    def run(self):
        while not self.halted:
            ins = self.IMEM.Read(self.PC)
            ex = executor.get(ins.opcode)
            ex(self, ins)
            # TODO for branch this is not correct
            self.PC = self.PC + 1

    @executor("ADD", "SUB", "AND", "OR", "XOR", "SLL", "SRL", "SRA")
    def exec_arithmetic_scalar(self, ins):
        a = self.SRF.Read(ins.src(0))
        b = self.SRF.Read(ins.src(1))
        # TODO switch case for each ins
        res = a + b
        self.SRF.Write(ins.dst(), res)

    @executor("CVM")
    def exec_cvm(self, ins):
        for i in range(Core.MVL):
            self.VM[i] = 1

    @executor("POP")
    def exec_pop(self, ins):
        count = BitVec.fromUnsigned(sum(self.VM))
        self.SRF.Write(ins.dst(), count)

    def dumpregs(self, iodir):
        self.SRF.dump(iodir)
        self.VRF.dump(iodir)
