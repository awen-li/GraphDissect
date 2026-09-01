#!/usr/bin/env python3
"""End-to-end integration test for the two user-facing entry scripts."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "experiments" / "tests"


def main() -> int:
    output = Path(tempfile.mkdtemp(prefix="graphdissect-entry-"))
    common = [
        "--subjects", str(TESTS / "subjects.json"),
        "--matrix", str(TESTS / "experiments.json"),
    ]
    try:
        run = subprocess.run([
            sys.executable, str(ROOT / "experiments" / "run_experiments.py"),
            *common, "--output", str(output), "--workers", "1",
            "--mfuzz", str(TESTS / "fake_mfuzz.py"),
        ], cwd=ROOT, check=False)
        assert run.returncode == 0, run.returncode
        collect = subprocess.run([
            sys.executable, str(ROOT / "experiments" / "collect_data.py"),
            *common, "--results", str(output),
        ], cwd=ROOT, check=False)
        assert collect.returncode == 0, collect.returncode
        assert (output / "collected" / "campaign_status.csv").is_file()
        assert (output / "collected" / "temporal" / "checkpoint_summary.csv").is_file()
        print("entry-script integration test passed")
        return 0
    finally:
        shutil.rmtree(output)


if __name__ == "__main__":
    raise SystemExit(main())
