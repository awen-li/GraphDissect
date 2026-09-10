#!/usr/bin/env python3
"""Remove oversized checkpoint snapshots while preserving analysis results.

Dry-run is the default. Use ``--apply`` only after stopping all campaigns.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("experiment-results"))
    parser.add_argument("--apply", action="store_true", help="delete checkpoint artifact directories")
    args = parser.parse_args()
    targets = []
    for path in args.results.glob("runs/*/*/*/*/trial-*/checkpoints"):
        if path.is_dir():
            targets.append(path)
    for path in args.results.glob("runs/*/*/*/*/trial-*/failed-runtime"):
        if path.is_dir():
            targets.append(path)
    total = sum(sum(item.stat().st_size for item in p.rglob("*") if item.is_file()) for p in targets)
    action = "Removing" if args.apply else "Would remove"
    print(f"{action} {len(targets)} snapshot directories ({total / (1024 ** 3):.2f} GiB)")
    if args.apply:
        for path in targets:
            shutil.rmtree(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
