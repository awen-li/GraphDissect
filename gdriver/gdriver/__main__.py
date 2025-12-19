import os
import argparse
from .drivergen import DriverGenerator

def main():
    parser = argparse.ArgumentParser(description="Option-based Driver Generator")
    parser.add_argument("binary_path", help="Path to the binary directory (e.g., ./libxml2/xmllint)")
    parser.add_argument("--binary", help="Binary name within the benchmark (e.g., xmllint)")

    args = parser.parse_args()

    if not args.binary_path:
        print("Please provide the binary path.")
        return

    gen = DriverGenerator(args.binary_path)
    if args.gen:
        if not gen.checkCached():
            gen.generate()
        gen.dump_driver_cmdlines()

if __name__ == "__main__":
    main()
