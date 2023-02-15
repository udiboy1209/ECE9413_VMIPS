# Author: Meet Udeshi, mdu2004
#
# Description: Implements BitVec class to manage Bit vectors as strings.

# BitVector stored as string
class BitVec:
    def __init__(self, bits):
        self.bits = bits
        self.length = len(self.bits)

    def __str__(self):
        return self.bits

    # For indexing into bits of BitVec.
    # Indexing is in reverse order, i.e. MSB:LSB.
    # Both MSB and LSB are included.
    def __getitem__(self, ref):
        if type(ref) == int:
            return int(self.bits[self.length - 1 - ref])
        elif type(ref) == slice:
            if ref.step is not None and ref.step != 1:
                raise NotImplementedError("Stride!=1 not supported")
            start = ref.start if ref.start is not None else self.length - 1
            stop = ref.stop if ref.stop is not None else 0
            if start < 0 or start >= self.length or stop < 0 or stop >= self.length:
                raise IndexError("Out of bounds")
            # Reverse access to properly implement MSB..LSB
            start = self.length - start - 1
            stop = self.length - stop
            newbs = self.bits[start:stop]
            return BitVec(newbs)
        else:
            raise IndexError

    # Number of bits
    def __len__(self):
        return self.length

    # Concatenate. RHS goes on LSB side.
    def __add__(self, rhs):
        newbs = self.bits + rhs.bits
        return BitVec(newbs)

    # Equality check
    def __eq__(self, rhs):
        return self.bits == str(rhs)

    def toUnsigned(self):
        return int(self.bits, 2)

    def toSigned(self):
        val = int(self.bits[1:], 2)
        if self.bits[0] == "1":
            val = val - 2 ** (self.length - 1)
        return val

    def fromUnsigned(num, length=None):
        bits = format(num, "b")
        if length:
            bits = bits.zfill(length)
            if len(bits) > length:
                bits = bits[-length:]
        return BitVec(bits)

    def fromSigned(num, length=None):
        length = length if length else 32
        # 2-s complement
        if num < 0:
            num = 2**length + num
        bits = format(num, "b")
        # Number will already be 1-filled if negative
        bits = bits.zfill(length)
        if len(bits) > length:
            bits = bits[-length:]
        return BitVec(bits)

    def zeroExtend(self, length):
        return BitVec(self.bits.zfill(length))

    def signExtend(self, length):
        if self.length >= length:
            return self
        if self.bits[0] == "0":
            return BitVec(self.bits.zfill(length))
        bits = ("1" * (length - self.length)) + self.bits
        return BitVec(bits)

    def twosCmpl(self):
        return BitVec.fromSigned(2**self.length - self.toSigned())


# Constants
ZERO32 = BitVec("0" * 32)
ONE32 = BitVec("0" * 31 + "1")
