#!/usr/bin/env python3
"""Verify and collect all campaign data into analysis-ready CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
import time

from run_campaigns import DEFAULT_MATRIX, DEFAULT_SUBJECTS, ROOT, expand, load_json, run_directory


CHECKPOINTS = {
    "temporal": [21600, 43200, 64800, 86400, 172800, 259200],
    "queue": [21600, 43200, 64800, 86400],
    "scheduling": [21600, 43200, 64800, 86400],
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--subjects", type=Path, default=DEFAULT_SUBJECTS)
    result.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    result.add_argument("--results", type=Path, default=ROOT / "experiment-results")
    result.add_argument("--output", type=Path)
    result.add_argument("--allow-incomplete", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    output = args.output or args.results / "collected"
    output.mkdir(parents=True, exist_ok=True)
    subjects = load_json(args.subjects)
    matrix = load_json(args.matrix)
    expected = expand(subjects, matrix, list(matrix["experiments"]))
    rows = []
    incomplete = []
    for run in expected:
        run_dir = run_directory(args.results, run)
        status_path = run_dir / "status.json"
        progress_path = run_dir / "progress.json"
        status = load_json(status_path) if status_path.is_file() else {"status": "missing"}
        progress = load_json(progress_path) if progress_path.is_file() else {}
        coverage = run_dir / "coverage.csv"
        row = {
            "run_id": run["run_id"], "experiment": run["experiment"],
            "benchmark": run["subject"]["benchmark"], "executable": run["subject"]["executable"],
            "condition": run["condition"]["name"], "trial": run["trial"],
            "status": status.get("status", "unknown"),
            "completed_seconds": progress.get("completed_seconds", status.get("completed_seconds", 0)),
            "expected_seconds": run["duration_seconds"], "coverage_csv": str(coverage),
            "coverage_exists": coverage.is_file(),
        }
        rows.append(row)
        if row["status"] != "complete" or not row["coverage_exists"]:
            incomplete.append(run["run_id"])
    status_csv = output / "campaign_status.csv"
    with status_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if incomplete and not args.allow_incomplete:
        print(f"Refusing partial collection: {len(incomplete)} of {len(expected)} campaigns are incomplete.", file=sys.stderr)
        print(f"Status report: {status_csv}", file=sys.stderr)
        return 2

    generated = []
    for experiment, checkpoints in CHECKPOINTS.items():
        destination = output / experiment
        command = [
            sys.executable, str(ROOT / "experiments" / "summarize_coverage.py"),
            "--results", str(args.results), "--experiment", experiment,
            "--output", str(destination), "--checkpoints", *map(str, checkpoints),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
        generated.append(str(destination))
    manifest = {
        "collected_unix": int(time.time()), "expected_campaigns": len(expected),
        "incomplete_campaigns": incomplete, "status_csv": str(status_csv),
        "analysis_directories": generated, "subjects_manifest": str(args.subjects.resolve()),
        "experiment_matrix": str(args.matrix.resolve()),
    }
    manifest_path = output / "collection_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Collected {len(expected) - len(incomplete)} complete campaigns into {output}")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
