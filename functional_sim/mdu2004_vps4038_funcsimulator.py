import os
import argparse

from imem import IMEM
from dmem import DMEM
from core import Core

if __name__ == "__main__":
    # parse arguments for input file location
    parser = argparse.ArgumentParser(description="Vector Core Performance Model")
    parser.add_argument(
        "--iodir",
        default="",
        type=str,
        help="Path to the folder containing the input files - instructions and data.",
    )
    parser.add_argument("--trace", default=False, action='store_true', help="Generate execution trace")
    args = parser.parse_args()

    iodir = os.path.abspath(args.iodir)
    print("IO Directory:", iodir)

    # Parse IMEM
    imem = IMEM(iodir)
    # Parse SMEM
    sdmem = DMEM("SDMEM", iodir, 13)  # 32 KB is 2^15 bytes = 2^13 K 32-bit words.
    # Parse VMEM
    vdmem = DMEM("VDMEM", iodir, 17)  # 512 KB is 2^19 bytes = 2^17 K 32-bit words.

    # Create Vector Core
    vcore = Core(imem, sdmem, vdmem, trace=args.trace)

    # Run Core
    vcore.run()
    vcore.dumpregs(iodir)
    vcore.dumptrace(iodir)

    sdmem.dump()
    vdmem.dump()

    # THE END
