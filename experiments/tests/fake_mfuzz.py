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
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--schedule", required=True)
    parser.add_argument("--queue-policy", required=True)
    parser.add_argument("--window", type=int, required=True)
    parser.add_argument("--checkpoint", type=int, required=True)
    parser.add_argument("--random-seed", type=int, required=True)
    parser.add_argument("--elapsed-offset", type=int, required=True)
    parser.add_argument("--drivers")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.output_dir / "checkpoint.json"
    if args.resume:
        if not state_path.is_file():
            raise SystemExit("--resume requested without persisted state")
        state = json.loads(state_path.read_text())
        if int(state["elapsed_seconds"]) != args.elapsed_offset:
            raise SystemExit("elapsed offset does not match persisted state")
    elif args.elapsed_offset != 0:
        raise SystemExit("nonzero elapsed offset requires --resume")
    fail_offset = os.environ.get("FAKE_MFUZZ_FAIL_OFFSET")
    if fail_offset is not None and int(fail_offset) == args.elapsed_offset:
        return 75
    elapsed = args.elapsed_offset + args.duration
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"elapsed_seconds": elapsed, "random_seed": args.random_seed}) + "\n")
    temporary.replace(state_path)
    coverage_path = args.output_dir / "coverage.csv"
    new_file = not coverage_path.exists()
    with coverage_path.open("a", newline="") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(["elapsed_seconds", "cg_nodes", "cfg_edges"])
        writer.writerow([elapsed, elapsed // max(1, args.checkpoint), 2 * elapsed // max(1, args.checkpoint)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
