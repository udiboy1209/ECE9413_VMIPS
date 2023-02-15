import os


class DMEM(object):
    # Word addressible - each address contains 32 bits.
    def __init__(self, name, iodir, addressLen):
        self.name = name
        self.size = pow(2, addressLen)
        self.min_value = -pow(2, 31)
        self.max_value = pow(2, 31) - 1
        self.ipfilepath = os.path.abspath(os.path.join(iodir, name + ".txt"))
        self.opfilepath = os.path.abspath(os.path.join(iodir, name + "OP.txt"))
        self.data = []

        with open(self.ipfilepath, "r") as ipf:
            self.data = [int(line.strip()) for line in ipf.readlines()]
        print(self.name, "- Data loaded from file:", self.ipfilepath)
        # print(self.name, "- Data:", self.data)
        self.data.extend([0x0 for i in range(self.size - len(self.data))])

    def Read(self, idx):  # Use this to read from DMEM.
        pass  # Replace this line with your code here.

    def Write(self, idx, val):  # Use this to write into DMEM.
        pass  # Replace this line with your code here.

    def dump(self):
        with open(self.opfilepath, "w") as opf:
            lines = [str(data) + "\n" for data in self.data]
            opf.writelines(lines)
        print(self.name, "- Dumped data into output file in path:", self.opfilepath)
