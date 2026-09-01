#!/usr/bin/env python3
"""Summarize run-level checkpoint coverage without unioning trials."""

from __future__ import annotations

import argparse
import csv
import json
import itertools
from pathlib import Path
import random
import statistics
from typing import Iterable


METRICS = ("cg_nodes", "cfg_edges")


def load_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"elapsed_seconds", *METRICS}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        rows = [{key: float(row[key]) for key in required} for row in reader]
    if not rows:
        raise ValueError(f"{path}: no coverage rows")
    return sorted(rows, key=lambda row: row["elapsed_seconds"])


def at_checkpoint(rows: list[dict[str, float]], checkpoint: int) -> dict[str, float]:
    eligible = [row for row in rows if row["elapsed_seconds"] <= checkpoint]
    if not eligible:
        raise ValueError(f"no observation at or before checkpoint {checkpoint}")
    return eligible[-1]


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def bootstrap_median_ci(values: list[float], seed: int, iterations: int = 10000) -> tuple[float, float]:
    if not values:
        raise ValueError("cannot bootstrap an empty sample")
    generator = random.Random(seed)
    samples = [statistics.median(generator.choices(values, k=len(values))) for _ in range(iterations)]
    return percentile(samples, 0.025), percentile(samples, 0.975)


def completed_runs(results: Path, experiment: str) -> Iterable[tuple[dict, Path]]:
    experiment_root = results / "runs" / experiment
    for provenance_path in sorted(experiment_root.glob("*/*/*/trial-*/provenance.json")):
        run_dir = provenance_path.parent
        status_path = run_dir / "status.json"
        coverage_path = run_dir / "coverage.csv"
        if not (status_path.is_file() and provenance_path.is_file() and coverage_path.is_file()):
            continue
        if json.loads(status_path.read_text())["status"] != "complete":
            continue
        yield json.loads(provenance_path.read_text()), coverage_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--experiment", default="temporal")
    parser.add_argument("--checkpoints", type=int, nargs="+", default=[21600, 43200, 64800, 86400, 172800, 259200])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.results / "analysis" / args.experiment
    output.mkdir(parents=True, exist_ok=True)

    values: list[dict[str, object]] = []
    for provenance, coverage_path in completed_runs(args.results, args.experiment):
        rows = load_rows(coverage_path)
        for checkpoint in args.checkpoints:
            observed = at_checkpoint(rows, checkpoint)
            for metric in METRICS:
                values.append({
                    "benchmark": provenance["subject"]["benchmark"],
                    "executable": provenance["subject"]["executable"],
                    "condition": provenance["condition"]["name"],
                    "trial": provenance["trial"],
                    "checkpoint_seconds": checkpoint,
                    "metric": metric,
                    "value": observed[metric],
                    "observed_elapsed_seconds": observed["elapsed_seconds"],
                })
    if not values:
        raise SystemExit("no completed runs with coverage.csv were found")

    raw_path = output / "checkpoint_values.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)

    grouped: dict[tuple, list[float]] = {}
    for row in values:
        key = (row["benchmark"], row["executable"], row["condition"], row["checkpoint_seconds"], row["metric"])
        grouped.setdefault(key, []).append(float(row["value"]))
    summary_path = output / "checkpoint_summary.csv"
    fields = ["benchmark", "executable", "condition", "checkpoint_seconds", "metric", "n", "median", "minimum", "maximum", "bootstrap_ci_low", "bootstrap_ci_high"]
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, (key, sample) in enumerate(sorted(grouped.items())):
            low, high = bootstrap_median_ci(sample, seed=20260416 + index)
            writer.writerow(dict(zip(fields[:5], key)) | {
                "n": len(sample), "median": statistics.median(sample), "minimum": min(sample), "maximum": max(sample),
                "bootstrap_ci_low": low, "bootstrap_ci_high": high,
            })
    indexed = {
        (row["benchmark"], row["executable"], row["condition"], row["trial"], row["checkpoint_seconds"], row["metric"]): float(row["value"])
        for row in values
    }
    conditions = sorted({str(row["condition"]) for row in values})
    paired_path = output / "paired_differences.csv"
    paired_fields = ["benchmark", "executable", "condition_a", "condition_b", "checkpoint_seconds", "metric", "n_pairs", "median_b_minus_a", "bootstrap_ci_low", "bootstrap_ci_high"]
    paired_rows = []
    subjects = sorted({(str(row["benchmark"]), str(row["executable"])) for row in values})
    for benchmark, executable in subjects:
        for condition_a, condition_b in itertools.combinations(conditions, 2):
            for checkpoint in args.checkpoints:
                for metric in METRICS:
                    differences = []
                    for trial in sorted({int(row["trial"]) for row in values}):
                        key_a = (benchmark, executable, condition_a, trial, checkpoint, metric)
                        key_b = (benchmark, executable, condition_b, trial, checkpoint, metric)
                        if key_a in indexed and key_b in indexed:
                            differences.append(indexed[key_b] - indexed[key_a])
                    if differences:
                        low, high = bootstrap_median_ci(differences, seed=20260416 + len(paired_rows))
                        paired_rows.append({
                            "benchmark": benchmark, "executable": executable, "condition_a": condition_a,
                            "condition_b": condition_b, "checkpoint_seconds": checkpoint, "metric": metric,
                            "n_pairs": len(differences), "median_b_minus_a": statistics.median(differences),
                            "bootstrap_ci_low": low, "bootstrap_ci_high": high,
                        })
    with paired_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=paired_fields)
        writer.writeheader()
        writer.writerows(paired_rows)
    print(raw_path)
    print(summary_path)
    print(paired_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
