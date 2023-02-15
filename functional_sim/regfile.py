import os
from util import BitVec


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
        try:
            return Reg(s[:2], int(s[2:]))
        except Exception as e:
            # print(s, e)
            return None


class RegisterFile(object):
    def __init__(self, ty, count, length=1, size=32):
        self.ty = ty
        self.name = ty + "F"
        self.reg_count = count
        self.vec_length = length  # words in a vector.
        self.reg_bits = size
        self.min_value = -pow(2, self.reg_bits - 1)
        self.max_value = pow(2, self.reg_bits - 1) - 1
        zerobits = "0" * self.reg_bits
        # Register file as list of lists
        self.registers = [
            [BitVec(zerobits) for e in range(self.vec_length)]
            for r in range(self.reg_count)
        ]

    def Read(self, reg):
        assert reg.ty == self.ty
        # Reg names are 1-indexed
        if self.vec_length == 1:
            # Read scalar directly, don't pass list of 1 element
            return self.registers[reg.idx - 1][0]
        else:
            return self.registers[reg.idx - 1]

    def Write(self, reg, val):
        assert reg.ty == self.ty
        if self.vec_length == 1:
            self.registers[reg.idx][0] = val
        else:
            self.registers[reg.idx] = val

    def dump(self, iodir):
        opfilepath = os.path.abspath(os.path.join(iodir, self.name + ".txt"))
        with open(opfilepath, "w") as opf:
            row_format = "{:<13}" * self.vec_length + "\n"
            lines = [
                row_format.format(*[str(i) for i in range(self.vec_length)]),
                "-" * (self.vec_length * 13) + "\n",
            ]
            lines += [
                row_format.format(*[str(val.toSigned()) for val in data])
                for data in self.registers
            ]
            opf.writelines(lines)
        print(self.name, "- Dumped data into output file in path:", opfilepath)
