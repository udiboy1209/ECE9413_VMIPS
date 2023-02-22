import os
from regfile import Reg


class Instruction(object):
    # Helper class to hold instructions and
    # provide access to operands and immediate value
    def __init__(self, line):
        if len(line) == 0:
            raise Exception("Empty instruction line")

        splits = line.split(" ")
        self.opcode = splits[0]
        self.ops = [Instruction.parse_operand(s) for s in splits[1:]]

    @staticmethod
    def parse_operand(opstr):
        sr = Reg.parse(opstr)
        if not sr:
            return int(opstr)
        else:
            return sr

    def num_ops(self):
        return len(self.ops)

    def op(self, idx):
        # Return the operand `idx`
        return self.ops[idx]

    def dst(self):
        # Return the destination operand i.e. ops[0]
        # WARN: not always correct, use op()
        return self.ops[0]

    def src(self, idx):
        # Return the source operand `idx` i.e. ops[idx + 1]
        # WARN: not always correct, use op()
        return self.ops[idx + 1]

    def imm(self):
        # Return the immediate operand i.e. ops[2]
        # WARN: not always correct, use op()
        return self.ops[2]

    def __repr__(self):
        return f"{self.opcode} {self.ops}"


class IMEM(object):
    def __init__(self, iodir):
        self.size = pow(2, 16)  # Can hold a maximum of 2^16 instructions.
        self.filepath = os.path.abspath(os.path.join(iodir, "Code.asm"))
        self.instructions = []

        with open(self.filepath, "r") as insf:
            for line in insf:
                # Ignore comments
                if "#" in line:
                    line = line[: line.index("#")]
                line = line.strip()
                if line:
                    self.instructions.append(Instruction(line))
        print("IMEM - Instructions loaded from file:", self.filepath)

    def Read(self, idx):  # Use this to read from IMEM.
        if idx < len(self.instructions):
            return self.instructions[idx]
        elif idx < self.size:
            return HALT  # If accessing undefined instructions, return HALT
        else:
            raise IndexError(
                f"IMEM - ERROR: Invalid memory access at index: {idx}, with memory size: {self.size}"
            )


HALT = Instruction("HALT")
