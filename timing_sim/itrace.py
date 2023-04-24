import os

class Reg(object):
    """
    Defines name of architectural registers.
    Scalar: SR0 - SR7
    Vector: VR0 - VR7
    """

    SCALAR = "SR"
    VECTOR = "VR"

    def __init__(self, ty=SCALAR, idx=1):
        if ty not in {Reg.SCALAR, Reg.VECTOR}:
            raise Exception(f"Invalid type: {ty}")
        if idx < 0 or idx > 7:
            raise Exception(f"Invalid index: {idx}")
        self.ty = ty
        self.idx = idx

    def __repr__(self):
        return f"{self.ty}{self.idx}"

    def __eq__(self, other):
        return self.ty == other.ty and self.idx == other.idx

    @staticmethod
    def parse(s):
        # Parse string and determine register type and index
        try:
            return Reg(s[:2], int(s[2:]))
        except Exception as e:
            # print(s, e)
            return None

class Instruction(object):
    # Helper class to hold instructions and
    # provide access to operands and immediate value
    def __init__(self, line, idx=-1):
        if len(line) == 0:
            raise Exception("Empty instruction line")

        splits = line.split(" ")
        self.opcode = splits[0]
        self.value = Instruction.parse_value(splits[-1])
        if self.value is not None:
            self.ops = [Instruction.parse_operand(s) for s in splits[1:-1]]
        else:
            self.ops = [Instruction.parse_operand(s) for s in splits[1:]]
        self.idx = idx

    @staticmethod
    def parse_value(valuestr):
        if valuestr.startswith('(') and valuestr.endswith(')'):
            value = [int(v) for v in valuestr[1:-1].split(',')]
            if len(value) == 1:
                value = value[0]
            return value
        return None

    @staticmethod
    def parse_operand(opstr):
        sr = Reg.parse(opstr)
        if not sr:
            try:
                return int(opstr)
            except:
                return sr
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
        if self.idx >= 0:
            return f"{self.idx}:{self.opcode}:{self.ops}"
        else:
            return f"{self.opcode}:{self.ops}"


class ITrace(object):
    def __init__(self, iodir):
        self.filepath = os.path.abspath(os.path.join(iodir, "trace.txt"))
        self.instructions = []

        with open(self.filepath, "r") as insf:
            idx = 0
            for line in insf:
                # Ignore comments
                if "#" in line:
                    line = line[: line.index("#")]
                line = line.strip()
                if line:
                    self.instructions.append(Instruction(line, idx))
                    idx += 1
        print("ITrace - Instruction trace loaded from file:", self.filepath)

    def Read(self, idx):
        if idx < len(self.instructions):
            return self.instructions[idx]
        else:
            return HALT  # If accessing undefined instructions, return HALT

HALT = Instruction("HALT")
