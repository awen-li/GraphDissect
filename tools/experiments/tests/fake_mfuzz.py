#!/usr/bin/env python3
"""Fast stateful stand-in used to integration-test campaign resumption."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-b", required=True)
    parser.add_argument("-t", type=int, required=True)
    parser.add_argument("-s", required=True)
    parser.add_argument("-q", required=True)
    parser.add_argument("-w", type=int, required=True)
    parser.add_argument("-r", type=int, required=True)
    args = parser.parse_args()
    output_dir = Path(os.environ["GRAPHDISSECT_RUN_DIR"])
    output_dir.mkdir(parents=True, exist_ok=True)
    state_path = output_dir / "checkpoint.json"
    elapsed_offset = int(os.environ.get("GRAPHDISSECT_ELAPSED_OFFSET", "0"))
    fail_offset = os.environ.get("FAKE_MFUZZ_FAIL_OFFSET")
    if fail_offset is not None and int(fail_offset) == elapsed_offset:
        return 75
    elapsed = elapsed_offset + args.t
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"elapsed_seconds": elapsed, "random_seed": args.r}) + "\n")
    temporary.replace(state_path)
    coverage_path = output_dir / "coverage.csv"
    new_file = not coverage_path.exists()
    with coverage_path.open("a", newline="") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(["elapsed_seconds", "cg_nodes", "cfg_edges"])
        writer.writerow([elapsed, elapsed // max(1, args.w), 2 * elapsed // max(1, args.w)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
