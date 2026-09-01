#!/usr/bin/env python3
"""Plan, validate, and run reproducible GraphDissect revision campaigns.

The runner intentionally refuses to use the legacy MFuzz CLI for real runs:
that CLI cannot isolate outputs or select queue/scheduling policies.  A real
run requires the revision CLI contract documented in README.md.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUBJECTS = ROOT / "experiments" / "subjects.json"
DEFAULT_MATRIX = ROOT / "experiments" / "experiments.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(path)


def stable_seed(base: int, *parts: object) -> int:
    digest = hashlib.sha256("\0".join(map(str, parts)).encode()).digest()
    return (base + int.from_bytes(digest[:4], "big")) % 2147483647


def expand(subjects: dict[str, Any], matrix: dict[str, Any], names: Iterable[str]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    base_seed = int(matrix["base_seed"])
    trials = int(matrix["trials"])
    for experiment_name in names:
        experiment = matrix["experiments"][experiment_name]
        for subject in subjects["subjects"]:
            for condition in experiment["conditions"]:
                for trial in range(1, trials + 1):
                    run_id = f"{experiment_name}__{subject['benchmark']}__{subject['executable']}__{condition['name']}__t{trial:02d}"
                    runs.append({
                        "run_id": run_id,
                        "experiment": experiment_name,
                        "subject": subject,
                        "condition": condition,
                        "trial": trial,
                        "random_seed": stable_seed(base_seed, experiment_name, subject["benchmark"], subject["executable"], condition["name"], trial),
                        "duration_seconds": int(experiment["duration_seconds"]),
                        "checkpoint_seconds": int(experiment["checkpoint_seconds"]),
                        "window_seconds": int(experiment.get("window_seconds", 900)),
                        "segment_seconds": int(matrix.get("segment_seconds", experiment["checkpoint_seconds"])),
                    })
    return runs


def driver_ids(subject_dir: Path) -> list[int]:
    listing = subject_dir / "drivers" / "driver_list.json"
    data = load_json(listing)
    return sorted(int(next(iter(entry))) for entry in data["drivers"])


def validate_run(run: dict[str, Any], mfuzz: Path, require_binary: bool) -> list[str]:
    errors: list[str] = []
    subject = run["subject"]
    subject_dir = ROOT / subject["path"]
    for relative in ("cmdspec.yaml", "drivers/driver_list.json"):
        if not (subject_dir / relative).is_file():
            errors.append(f"missing {subject_dir / relative}")
    if (subject_dir / "drivers" / "driver_list.json").is_file():
        ids = driver_ids(subject_dir)
        if len(ids) != int(subject["driver_count"]):
            errors.append(f"driver count mismatch: manifest={subject['driver_count']} actual={len(ids)}")
        best = subject.get("best_driver_id")
        if run["condition"].get("requires_best_driver") and best is None:
            errors.append("best_driver_id is required for the single-driver condition")
        if best is not None and int(best) not in ids:
            errors.append(f"best_driver_id {best} is not present in driver_list.json")
    if require_binary:
        resolved = shutil.which(str(mfuzz)) if not mfuzz.is_absolute() else str(mfuzz)
        if not resolved or not Path(resolved).is_file():
            errors.append(f"MFuzz revision binary not found: {mfuzz}")
    return errors


def validate_mfuzz_contract(mfuzz: Path) -> list[str]:
    required = ("--benchmark", "--duration", "--output-dir", "--schedule", "--queue-policy",
                "--window", "--checkpoint", "--random-seed", "--elapsed-offset", "--resume")
    try:
        result = subprocess.run([str(mfuzz), "--help"], check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"unable to inspect MFuzz CLI: {exc}"]
    help_text = result.stdout + result.stderr
    missing = [option for option in required if option not in help_text]
    return [f"MFuzz revision CLI is missing: {', '.join(missing)}"] if missing else []


def command_for(run: dict[str, Any], mfuzz: Path, run_dir: Path, duration: int | None = None,
                elapsed_offset: int = 0, resume: bool = False) -> list[str]:
    condition = run["condition"]
    command = [
        str(mfuzz),
        "--benchmark", str((ROOT / run["subject"]["path"]).resolve()),
        "--duration", str(duration if duration is not None else run["duration_seconds"]),
        "--output-dir", str(run_dir.resolve()),
        "--schedule", condition["schedule"],
        "--queue-policy", condition["queue"],
        "--window", str(run["window_seconds"]),
        "--checkpoint", str(run["checkpoint_seconds"]),
        "--random-seed", str(run["random_seed"]),
        "--elapsed-offset", str(elapsed_offset),
    ]
    if condition.get("requires_best_driver"):
        best_driver = run["subject"].get("best_driver_id")
        command.extend(["--drivers", str(best_driver) if best_driver is not None else "<REQUIRED>"])
    if resume:
        command.append("--resume")
    return command


def write_plan(runs: list[dict[str, Any]], output: Path, mfuzz: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    plan_path = output / "plan.csv"
    with plan_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "experiment", "benchmark", "executable", "condition", "trial", "seed", "duration_seconds", "command"])
        for run in runs:
            run_dir = output / "runs" / run["run_id"]
            writer.writerow([
                run["run_id"], run["experiment"], run["subject"]["benchmark"], run["subject"]["executable"],
                run["condition"]["name"], run["trial"], run["random_seed"], run["duration_seconds"],
                json.dumps(command_for(run, mfuzz, run_dir)),
            ])
    return plan_path


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def acquire_lock(lock_path: Path, recover_foreign: bool = False) -> None:
    if lock_path.exists():
        try:
            owner = load_json(lock_path)
        except (OSError, ValueError, json.JSONDecodeError):
            owner = {}
        same_host = owner.get("hostname") == socket.gethostname()
        owner_pid = int(owner.get("pid", -1))
        if same_host and owner_pid > 0 and process_alive(owner_pid):
            raise RuntimeError(f"campaign is locked by live pid {owner_pid}")
        if not same_host and not recover_foreign:
            raise RuntimeError(
                f"campaign lock belongs to host {owner.get('hostname', 'unknown')}; "
                "use --recover-foreign-lock only after verifying that host/job is dead"
            )
        lock_path.unlink(missing_ok=True)
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        raise RuntimeError("campaign lock was acquired concurrently") from exc
    payload = json.dumps({"pid": os.getpid(), "hostname": socket.gethostname(), "created_unix": int(time.time())}) + "\n"
    os.write(lock_fd, payload.encode())
    os.close(lock_fd)


def reconcile_checkpoint(run_dir: Path, progress: dict[str, Any], total_seconds: int) -> int:
    """Trust an atomically committed MFuzz checkpoint if it is ahead of runner state."""
    checkpoint_path = run_dir / "checkpoint.json"
    completed = int(progress.get("completed_seconds", 0))
    if not checkpoint_path.is_file():
        return completed
    checkpoint = load_json(checkpoint_path)
    committed = int(checkpoint.get("elapsed_seconds", -1))
    if committed < completed or committed > total_seconds:
        raise RuntimeError(f"invalid committed checkpoint {committed}; runner progress is {completed}")
    if committed > completed:
        progress["completed_seconds"] = committed
        progress.setdefault("recovered_checkpoints", []).append({
            "elapsed_seconds": committed, "recovered_unix": int(time.time())
        })
        atomic_json(run_dir / "progress.json", progress)
    return committed


def run_one(run: dict[str, Any], output: Path, mfuzz: Path, force: bool,
            recover_foreign_lock: bool) -> str:
    run_dir = output / "runs" / run["run_id"]
    status_path = run_dir / "status.json"
    if status_path.is_file() and not force:
        status = load_json(status_path).get("status")
        if status == "complete":
            return "skipped"
    run_dir.mkdir(parents=True, exist_ok=True)
    lock_path = run_dir / ".lock"
    acquire_lock(lock_path, recover_foreign=recover_foreign_lock)
    progress_path = run_dir / "progress.json"
    progress = load_json(progress_path) if progress_path.is_file() and not force else {
        "completed_seconds": 0, "completed_segments": [], "total_seconds": run["duration_seconds"]
    }
    completed_seconds = reconcile_checkpoint(run_dir, progress, run["duration_seconds"])
    if completed_seconds < 0 or completed_seconds > run["duration_seconds"]:
        lock_path.unlink(missing_ok=True)
        raise RuntimeError(f"invalid completed_seconds in {progress_path}")
    first_duration = min(run["segment_seconds"], run["duration_seconds"] - completed_seconds)
    command = command_for(run, mfuzz, run_dir, duration=first_duration,
                          elapsed_offset=completed_seconds, resume=completed_seconds > 0)
    provenance = {
        **run,
        "subject": dict(run["subject"]),
        "command_template": command,
        "repository": str(ROOT),
        "started_unix": int(time.time()),
    }
    atomic_json(run_dir / "provenance.json", provenance)
    atomic_json(status_path, {"status": "running", "started_unix": provenance["started_unix"]})
    try:
        while completed_seconds < run["duration_seconds"]:
            segment_number = len(progress["completed_segments"]) + 1
            segment_duration = min(run["segment_seconds"], run["duration_seconds"] - completed_seconds)
            command = command_for(run, mfuzz, run_dir, duration=segment_duration,
                                  elapsed_offset=completed_seconds, resume=completed_seconds > 0)
            segment_record = {
                "segment": segment_number, "elapsed_offset": completed_seconds,
                "duration_seconds": segment_duration, "command": command,
                "started_unix": int(time.time()),
            }
            atomic_json(run_dir / "current_segment.json", segment_record)
            with (run_dir / "stdout.log").open("ab") as stdout, (run_dir / "stderr.log").open("ab") as stderr:
                completed = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
            segment_record["returncode"] = completed.returncode
            segment_record["finished_unix"] = int(time.time())
            if completed.returncode != 0:
                atomic_json(run_dir / "last_failed_segment.json", segment_record)
                final = {"status": "failed", "returncode": completed.returncode,
                         "completed_seconds": completed_seconds, "finished_unix": int(time.time())}
                atomic_json(status_path, final)
                return "failed"
            completed_seconds += segment_duration
            progress["completed_seconds"] = completed_seconds
            progress["completed_segments"].append(segment_record)
            atomic_json(progress_path, progress)
            (run_dir / "current_segment.json").unlink(missing_ok=True)
        final = {"status": "complete", "returncode": 0, "completed_seconds": completed_seconds,
                 "finished_unix": int(time.time())}
        atomic_json(status_path, final)
        return final["status"]
    finally:
        lock_path.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("plan", "validate", "run"))
    result.add_argument("--subjects", type=Path, default=DEFAULT_SUBJECTS)
    result.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    result.add_argument("--experiments", nargs="+", default=["temporal", "queue", "scheduling"])
    result.add_argument("--output", type=Path, default=ROOT / "experiment-results")
    result.add_argument("--mfuzz", type=Path, default=ROOT / "mfuzz" / "build" / "mfuzz")
    result.add_argument("--run-id", help="run exactly one expanded campaign")
    result.add_argument("--force", action="store_true")
    result.add_argument("--recover-foreign-lock", action="store_true",
                        help="reclaim a lock from another host after independently verifying its job is dead")
    return result


def main() -> int:
    args = parser().parse_args()
    subjects = load_json(args.subjects)
    matrix = load_json(args.matrix)
    unknown = sorted(set(args.experiments) - set(matrix["experiments"]))
    if unknown:
        raise SystemExit(f"unknown experiments: {', '.join(unknown)}")
    runs = expand(subjects, matrix, args.experiments)
    if args.run_id:
        runs = [run for run in runs if run["run_id"] == args.run_id]
        if not runs:
            raise SystemExit(f"unknown run id: {args.run_id}")
    plan_path = write_plan(runs, args.output, args.mfuzz)
    failures = [(run["run_id"], validate_run(run, args.mfuzz, args.action != "plan")) for run in runs]
    failures = [(run_id, errors) for run_id, errors in failures if errors]
    if args.action in {"plan", "validate"}:
        print(f"planned {len(runs)} campaigns in {plan_path}")
        if failures:
            for run_id, errors in failures:
                print(f"{run_id}: {'; '.join(errors)}", file=sys.stderr)
            label = "planning warnings" if args.action == "plan" else "validation failed"
            print(f"{label} for {len(failures)} campaigns", file=sys.stderr)
            return 0 if args.action == "plan" else 2
        if args.action == "validate":
            contract_errors = validate_mfuzz_contract(args.mfuzz)
            if contract_errors:
                for error in contract_errors:
                    print(error, file=sys.stderr)
                return 2
        print("validation passed")
        return 0
    if failures:
        for run_id, errors in failures:
            print(f"{run_id}: {'; '.join(errors)}", file=sys.stderr)
        return 2
    contract_errors = validate_mfuzz_contract(args.mfuzz)
    if contract_errors:
        for error in contract_errors:
            print(error, file=sys.stderr)
        return 2
    counts: dict[str, int] = {}
    for run in runs:
        status = run_one(run, args.output, args.mfuzz, args.force, args.recover_foreign_lock)
        counts[status] = counts.get(status, 0) + 1
        print(f"{run['run_id']}: {status}")
    print(json.dumps(counts, sort_keys=True))
    return 0 if not counts.get("failed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
