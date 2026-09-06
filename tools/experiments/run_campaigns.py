#!/usr/bin/env python3
"""Plan, validate, and run reproducible GraphDissect revision campaigns.

MFuzz continues to write into its benchmark directory. This runner copies
those mutable runtime artifacts after every segment; single-driver campaigns
use the existing benchmark configurations under ``benchmarks/baseline``.
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
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUBJECTS = ROOT / "experiments" / "subjects.json"
DEFAULT_MATRIX = ROOT / "experiments" / "experiments.json"
RUNTIME_ARTIFACTS = (
    "driver_runtimes", "final_marked_callgraph.dot", "fuzz",
    "honggfuzz_profiling.txt", "mfuzz_drv_switch_cost.log", "mfuzz_f_coverage.log",
)
SCHEDULE_OPTIONS = {
    "fixed_round_robin": "fixed", "single": "fixed",
    "random_round": "random", "coverage_progress": "progress",
}
_ACTIVE_PIDS: set[int] = set()
_ACTIVE_PIDS_LOCK = threading.Lock()


def terminate_active_processes() -> None:
    with _ACTIVE_PIDS_LOCK:
        pids = list(_ACTIVE_PIDS)
    for pid in pids:
        try:
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shared_input_manifest(subject_dir: Path) -> list[dict[str, Any]]:
    candidates = [subject_dir / "cmdspec.yaml", subject_dir / "drivers" / "driver_list.json"]
    candidates.extend(sorted((subject_dir / "drivers").glob("*/*.json")))
    for name in ("callgraph.dot", "marked_callgraph.dot", "faddr_id.map"):
        candidates.append(subject_dir / name)
    manifest = []
    for path in candidates:
        if path.is_file():
            manifest.append({
                "path": str(path.resolve()), "relative_path": str(path.relative_to(subject_dir)),
                "size_bytes": path.stat().st_size, "sha256": file_sha256(path),
            })
    return manifest


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


def benchmark_directory(run: dict[str, Any]) -> Path:
    if run["condition"].get("requires_best_driver"):
        configured = run["subject"].get("baseline_path")
        if configured:
            return (ROOT / configured).resolve()
        relative = Path(run["subject"]["path"])
        return (ROOT / relative.parent.parent / "baseline" / relative.parent.name / relative.name).resolve()
    return (ROOT / run["subject"]["path"]).resolve()


def validate_run(run: dict[str, Any], mfuzz: Path, require_binary: bool) -> list[str]:
    errors: list[str] = []
    subject = run["subject"]
    subject_dir = benchmark_directory(run)
    for relative in ("cmdspec.yaml", "drivers/driver_list.json"):
        if not (subject_dir / relative).is_file():
            errors.append(f"missing {subject_dir / relative}")
    if (subject_dir / "drivers" / "driver_list.json").is_file():
        ids = driver_ids(subject_dir)
        expected_drivers = 1 if run["condition"].get("requires_best_driver") else int(subject["driver_count"])
        if len(ids) != expected_drivers:
            errors.append(f"driver count mismatch: expected={expected_drivers} actual={len(ids)}")
    if require_binary:
        resolved = shutil.which(str(mfuzz)) if not mfuzz.is_absolute() else str(mfuzz)
        if not resolved or not Path(resolved).is_file():
            errors.append(f"MFuzz revision binary not found: {mfuzz}")
    return errors


def validate_mfuzz_contract(mfuzz: Path) -> list[str]:
    required = ("-b", "-t", "-s", "-q", "-w", "-r")
    try:
        result = subprocess.run([str(mfuzz), "-h"], check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"unable to inspect MFuzz CLI: {exc}"]
    help_text = result.stdout + result.stderr
    missing = [option for option in required if option not in help_text]
    return [f"MFuzz CLI is missing required options: {', '.join(missing)}"] if missing else []


def command_for(run: dict[str, Any], mfuzz: Path, run_dir: Path, duration: int | None = None,
                elapsed_offset: int = 0, resume: bool = False) -> list[str]:
    condition = run["condition"]
    command = [
        str(mfuzz),
        "-b", str(benchmark_directory(run)),
        "-t", str(duration if duration is not None else run["duration_seconds"]),
        "-s", SCHEDULE_OPTIONS[condition["schedule"]],
        "-q", condition["queue"],
        "-w", str(run["window_seconds"]),
        "-r", str(run["random_seed"]),
    ]
    return command


def snapshot_runtime(subject_dir: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_ARTIFACTS:
        source = subject_dir / name
        target = destination / name
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        elif source.is_file():
            shutil.copy2(source, target)


def clean_runtime(subject_dir: Path) -> None:
    """Remove only mutable campaign outputs; preserve binaries, graphs, seeds, and drivers."""
    for name in RUNTIME_ARTIFACTS:
        path = subject_dir / name
        if path.is_dir():
            try:
                shutil.rmtree(path)
            except OSError:
                # A stale fuzzer may still have an open writer. Rename first so
                # the new campaign gets a clean path, then remove what is safe.
                stale = path.with_name(f"{path.name}.stale-{os.getpid()}")
                try:
                    path.rename(stale)
                    shutil.rmtree(stale, ignore_errors=True)
                except FileNotFoundError:
                    pass
        elif path.exists():
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def append_coverage(run_dir: Path, snapshot: Path, elapsed_seconds: int) -> None:
    log = snapshot / "mfuzz_f_coverage.log"
    if not log.is_file():
        return
    values = [line.strip().split(",") for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not values:
        return
    edges = 0
    overview = snapshot / "driver_runtimes" / "overview.stat"
    if overview.is_file():
        fields = dict(
            field.strip().split(":", 1)
            for field in overview.read_text(encoding="utf-8").strip().split(",")
            if ":" in field
        )
        edges = int(fields.get("edges", 0))
    coverage = run_dir / "coverage.csv"
    new_file = not coverage.exists()
    with coverage.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(["elapsed_seconds", "cg_nodes", "cfg_edges"])
        writer.writerow([elapsed_seconds, int(values[-1][1]), edges])


def run_directory(output: Path, run: dict[str, Any]) -> Path:
    """Return a collision-free directory scoped by experiment and trial."""
    return (
        output / "runs" / run["experiment"] / run["subject"]["benchmark"] /
        run["subject"]["executable"] / run["condition"]["name"] /
        f"trial-{int(run['trial']):02d}"
    )


def write_plan(runs: list[dict[str, Any]], output: Path, mfuzz: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    plan_path = output / "plan.csv"
    with plan_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["run_id", "experiment", "benchmark", "executable", "condition", "trial", "seed", "duration_seconds", "command"])
        for run in runs:
            run_dir = run_directory(output, run)
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
    run_dir = run_directory(output, run)
    status_path = run_dir / "status.json"
    if status_path.is_file() and not force:
        status = load_json(status_path).get("status")
        if status == "complete":
            return "skipped"
    run_dir.mkdir(parents=True, exist_ok=True)
    subject_dir = benchmark_directory(run)
    if run_dir.resolve().is_relative_to(subject_dir):
        raise RuntimeError("runtime output directory must not be inside the shared benchmark directory")
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
    if completed_seconds == 0 and not progress.get("completed_segments"):
        clean_runtime(subject_dir)
    first_duration = min(run["segment_seconds"], run["duration_seconds"] - completed_seconds)
    command = command_for(run, mfuzz, run_dir, duration=first_duration,
                          elapsed_offset=completed_seconds, resume=completed_seconds > 0)
    provenance = {
        **run,
        "subject": dict(run["subject"]),
        "command_template": command,
        "repository": str(ROOT),
        "shared_benchmark_directory": str(subject_dir),
        "shared_inputs": shared_input_manifest(subject_dir),
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
                environment = os.environ.copy()
                environment["GRAPHDISSECT_RUN_DIR"] = str(run_dir.resolve())
                environment["GRAPHDISSECT_ELAPSED_OFFSET"] = str(completed_seconds)
                completed_process = subprocess.Popen(
                    command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                    start_new_session=True,
                )
                with _ACTIVE_PIDS_LOCK:
                    _ACTIVE_PIDS.add(completed_process.pid)
                try:
                    returncode = completed_process.wait()
                except KeyboardInterrupt:
                    try:
                        os.killpg(completed_process.pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass
                    completed_process.wait()
                    raise
                finally:
                    with _ACTIVE_PIDS_LOCK:
                        _ACTIVE_PIDS.discard(completed_process.pid)
                completed = subprocess.CompletedProcess(command, returncode)
            segment_record["returncode"] = completed.returncode
            segment_record["finished_unix"] = int(time.time())
            if completed.returncode != 0:
                snapshot_runtime(subject_dir, run_dir / "failed-runtime")
                atomic_json(run_dir / "last_failed_segment.json", segment_record)
                final = {"status": "failed", "returncode": completed.returncode,
                         "completed_seconds": completed_seconds, "finished_unix": int(time.time())}
                atomic_json(status_path, final)
                return "failed"
            completed_seconds += segment_duration
            snapshot = run_dir / "checkpoints" / f"elapsed-{completed_seconds:09d}"
            snapshot_runtime(subject_dir, snapshot)
            append_coverage(run_dir, snapshot, completed_seconds)
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
