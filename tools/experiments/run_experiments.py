#!/usr/bin/env python3
"""Run the complete TOSEM experiment matrix with one worker per executable.

Invoke this script again after interruption; completed campaigns are skipped
and incomplete campaigns resume from their last committed checkpoint.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

from run_campaigns import (
    DEFAULT_MATRIX,
    DEFAULT_SUBJECTS,
    ROOT,
    expand,
    load_json,
    run_one,
    terminate_active_processes,
    validate_mfuzz_contract,
    validate_run,
    write_plan,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--subjects", type=Path, default=DEFAULT_SUBJECTS)
    result.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    result.add_argument("--output", type=Path, default=ROOT / "experiment-results")
    result.add_argument("--mfuzz", type=Path, default=ROOT / "mfuzz" / "build" / "mfuzz")
    result.add_argument("--workers", type=int, default=8)
    result.add_argument("--recover-foreign-lock", action="store_true")
    result.add_argument("--validate-only", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    subjects = load_json(args.subjects)
    matrix = load_json(args.matrix)
    experiment_names = list(matrix["experiments"])
    runs = expand(subjects, matrix, experiment_names)
    plan = write_plan(runs, args.output, args.mfuzz)
    errors = []
    for run in runs:
        for error in validate_run(run, args.mfuzz, require_binary=True):
            errors.append(f"{run['run_id']}: {error}")
    errors.extend(validate_mfuzz_contract(args.mfuzz))
    if errors:
        print("Experiment validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    print(f"Validated {len(runs)} campaigns; plan: {plan}")
    if args.validate_only:
        return 0

    by_subject: dict[tuple[str, str], list[dict]] = {}
    for run in runs:
        key = (run["subject"]["benchmark"], run["subject"]["executable"])
        by_subject.setdefault(key, []).append(run)

    def run_subject(key: tuple[str, str], subject_runs: list[dict]) -> tuple[tuple[str, str], dict[str, int]]:
        counts: dict[str, int] = {}
        for run in subject_runs:
            status = run_one(run, args.output, args.mfuzz, force=False,
                             recover_foreign_lock=args.recover_foreign_lock)
            counts[status] = counts.get(status, 0) + 1
            print(f"[{key[0]}/{key[1]}] {run['run_id']}: {status}", flush=True)
            if status == "failed":
                break
        return key, counts

    total: dict[str, int] = {}
    failed = False
    workers = max(1, min(args.workers, len(by_subject)))
    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        futures = {executor.submit(run_subject, key, value): key for key, value in by_subject.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                _, counts = future.result()
            except Exception as exc:  # keep other executable workers alive
                failed = True
                print(f"[{key[0]}/{key[1]}] worker failed: {exc}", file=sys.stderr)
                continue
            for status, count in counts.items():
                total[status] = total.get(status, 0) + count
            failed = failed or counts.get("failed", 0) > 0
    except KeyboardInterrupt:
        print("Interrupted; terminating active campaign processes. Re-run to resume.", file=sys.stderr)
        terminate_active_processes()
        executor.shutdown(wait=False, cancel_futures=True)
        return 130
    else:
        executor.shutdown(wait=True)
    print("Campaign summary: " + ", ".join(f"{key}={value}" for key, value in sorted(total.items())))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
