import argparse
import sys
from pathlib import Path

from faddr2gid.faddr_gid import FaddrMap


def main() -> int:
    p = argparse.ArgumentParser(prog="FAddr2Gid")
    p.add_argument("--bench", required=True, help="Benchmark directory")
    p.add_argument("--binary", required=True, help="Main executable filename inside bench")
    args = p.parse_args()

    bench = str(Path(args.bench).resolve())
    m = FaddrMap(bench, args.binary)
    out = m.genFddrIdMap()
    print(f"Generated Faddr2Gid map: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
