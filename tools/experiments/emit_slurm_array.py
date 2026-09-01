#!/usr/bin/env python3
"""Emit a resumable Slurm array script from run_campaigns.py's plan.csv."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--max-concurrent", type=int, default=8)
    parser.add_argument("--time", default="3-06:00:00")
    parser.add_argument("--memory", default="6G")
    args = parser.parse_args()
    with args.plan.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit("plan contains no campaigns")
    repo = Path(__file__).resolve().parents[1]
    script = f"""#!/bin/bash
#SBATCH --job-name=graphdissect-revision
#SBATCH --array=0-{len(rows) - 1}%{args.max_concurrent}
#SBATCH --cpus-per-task=1
#SBATCH --mem={args.memory}
#SBATCH --time={args.time}
#SBATCH --output={args.results.resolve()}/slurm/%A_%a.out
#SBATCH --error={args.results.resolve()}/slurm/%A_%a.err
set -euo pipefail
mkdir -p {args.results.resolve()}/slurm
RUN_ID=$(sed -n \"$((SLURM_ARRAY_TASK_ID + 2))p\" {args.plan.resolve()} | cut -d, -f1)
if [ -z \"$RUN_ID\" ]; then
  echo \"Unable to resolve run ID for array index $SLURM_ARRAY_TASK_ID\" >&2
  exit 2
fi
python3 {repo}/tools/experiments/run_campaigns.py run --output {args.results.resolve()} --run-id \"$RUN_ID\"
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(script, encoding="utf-8")
    args.output.chmod(0o755)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
