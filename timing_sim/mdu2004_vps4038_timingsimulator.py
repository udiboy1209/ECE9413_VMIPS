import os
import argparse

from itrace import ITrace
from core import Core, Config

if __name__ == "__main__":
    # parse arguments for input file location
    parser = argparse.ArgumentParser(description="Vector Core Timing Model")
    parser.add_argument(
        "--iodir",
        default="",
        type=str,
        help="Path to the folder containing the input files - instructions and data.",
    )
    parser.add_argument("--cyclewise", default=False, action="store_true", help="Generate cycle-wise pipeline log")
    args = parser.parse_args()

    iodir = os.path.abspath(args.iodir)
    print("IO Directory:", iodir)

    # Parse Config
    config = Config(iodir)
    # Parse trace
    itrace = ITrace(iodir)
    # Create Vector Core
    vcore = Core(itrace, config, iodir, cyclewise=args.cyclewise)

    # Run Core
    cycles_taken = vcore.run()
    print("Cycles:", cycles_taken)

    # THE END
