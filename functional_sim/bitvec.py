# BitVector stored as integer
class BitVec:
    def __init__(self, val, length=32):
        self.val = val
        self.length = length
        self.mask = 2**length - 1
        self.val &= self.mask

    def __str__(self):
        return str(self.signed())
    def __repr__(self):
        return str(self.signed())

    # Number of bits
    def __len__(self):
        return self.length

    def signed(self):
        if self.val < 0:
            return self.val
        elif self.val > (self.mask // 2):
            self.val &= self.mask
            # Twos complement
            return -(self.mask - self.val + 1)
        else:
            return self.val
    def unsigned(self):
        self.val &= self.mask
        return self.val

    # Equality check
    def __eq__(self, rhs):
        return self.val == rhs.val and self.length == rhs.length

    def twosCmpl(self):
        return BitVec(self.mask - self.val + 1, self.length)

    @staticmethod
    def add(lhs, rhs):
        val = lhs.signed() + rhs.signed()
        return BitVec(val, lhs.length)

    @staticmethod
    def sub(lhs, rhs):
        val = lhs.signed() - rhs.signed()
        return BitVec(val, lhs.length)

    @staticmethod
    def mul(lhs, rhs):
        val = lhs.signed() * rhs.signed()
        return BitVec(val, lhs.length)

    @staticmethod
    def div(lhs, rhs):
        try:
            val = lhs.signed() // rhs.signed()
        except ZeroDivisionError:
            # Divide by zero saturates to max
            print("WARNING: Divide by zero detected")
            val = lhs.mask // 2
        return BitVec(val, lhs.length)

    @staticmethod
    def bitand(lhs, rhs):
        val = lhs.unsigned() & rhs.unsigned()
        return BitVec(val, lhs.length)

    @staticmethod
    def bitor(lhs, rhs):
        val = lhs.unsigned() | rhs.unsigned()
        return BitVec(val, lhs.length)

    @staticmethod
    def bitxor(lhs, rhs):
        val = lhs.unsigned() ^ rhs.unsigned()
        return BitVec(val, lhs.length)

    @staticmethod
    def sll(lhs, rhs):
        val = lhs.signed() << (rhs.unsigned() % lhs.length)
        return BitVec(val, lhs.length)

    @staticmethod
    def srl(lhs, rhs):
        shift = rhs.unsigned() % lhs.length
        val = (lhs.unsigned() >> shift) & (lhs.mask >> shift)
        return BitVec(val, lhs.length)

    @staticmethod
    def sra(lhs, rhs):
        val = lhs.signed() >> (rhs.unsigned() % lhs.length)
        return BitVec(val, lhs.length)

