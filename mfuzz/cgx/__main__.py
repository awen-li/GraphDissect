import argparse
import sys
from pathlib import Path
from cgx.cgx_map import CgxMap


def main() -> int:
    p = argparse.ArgumentParser(prog="CgxMap")
    p.add_argument("--bench", required=True, help="Benchmark directory")
    p.add_argument("--binary", required=True, help="Main executable filename inside bench")
    args = p.parse_args()

    bench = str(Path(args.bench).resolve())
    m = CgxMap(bench, args.binary)
    m.update_cgmap()
    print(f"build cgxmap for {args.binary} in {args.bench} done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
