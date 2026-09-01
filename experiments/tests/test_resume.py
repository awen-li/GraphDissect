#!/usr/bin/env python3
"""Integration test: fail one segment, then resume without repeating completed work."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def invoke(output: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    command = [
        sys.executable, str(ROOT / "experiments" / "run_campaigns.py"), "run",
        "--experiments", "queue", "--output", str(output),
        "--mfuzz", str(ROOT / "experiments" / "tests" / "fake_mfuzz.py"),
        "--run-id", "queue__snort3__snort__shared__t01",
    ]
    return subprocess.run(command, cwd=ROOT, env=environment, check=False, capture_output=True, text=True)


def main() -> int:
    output = Path(tempfile.mkdtemp(prefix="graphdissect-resume-"))
    try:
        environment = os.environ.copy()
        environment["FAKE_MFUZZ_FAIL_OFFSET"] = "7200"
        first = invoke(output, environment)
        assert first.returncode == 1, first.stderr
        run_dir = output / "runs" / "queue" / "snort3" / "snort" / "shared" / "trial-01"
        progress = json.loads((run_dir / "progress.json").read_text())
        assert progress["completed_seconds"] == 7200, progress
        # Simulate shutdown after MFuzz atomically committed hour two but before
        # the runner recorded the subprocess return.
        progress["completed_seconds"] = 3600
        progress["completed_segments"] = progress["completed_segments"][:1]
        (run_dir / "progress.json").write_text(json.dumps(progress))
        second = invoke(output)
        assert second.returncode == 0, second.stderr
        progress = json.loads((run_dir / "progress.json").read_text())
        assert progress["completed_seconds"] == 86400, progress
        assert len(progress["completed_segments"]) == 23, progress
        assert progress["recovered_checkpoints"][0]["elapsed_seconds"] == 7200, progress
        status = json.loads((run_dir / "status.json").read_text())
        assert status["status"] == "complete", status
        print("resume integration test passed")
        return 0
    finally:
        shutil.rmtree(output)


if __name__ == "__main__":
    raise SystemExit(main())
