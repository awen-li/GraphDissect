import os
import re
import json
import time
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Callable
import subprocess


class RunStatus(Enum):
    OK = "ok"            # command looks valid
    SOFT_FAIL = "soft_fail"  # likely invalid/unsupported, but not a crash
    HARD_FAIL = "hard_fail"  # crash / timeout / serious error (BUG)


@dataclass
class CommandCheckResult:
    status: RunStatus
    reason: str
    returncode: int
    stderr_snippet: str


PerToolValidator = Callable[[List[str], subprocess.CompletedProcess], Optional[CommandCheckResult]]


class RunChecker:
    """
    Centralized heuristic for deciding whether a test run of a driver
    (cmd + subprocess.CompletedProcess) should be treated as valid or invalid.

    On HARD_FAIL (crash / timeout / serious fault), it logs an entry
    to crash_log_path, if provided.
    """

    HARD_FAILURE_PATTERNS = [
        r"segmentation fault",
        r"segfault",
        r"core dumped",
        r"abort\(\)",
        r"\baborted\b",
        r"stack trace",
        r"sigsegv",
        r"sigabrt",
    ]

    USAGE_FAILURE_PATTERNS = [
        r"\busage[: ]",
        r"try '--help'",
        r"try \"--help\"",
        r"unrecognized option",
        r"unknown option",
        r"invalid option",
        r"invalid argument",
        r"missing (argument|operand)",
        r"required (argument|operand)",
        r"not found",
        r"error occur",
        r"error open",
        r"error happen"
    ]

    BENIGN_PATTERNS = [
        r"\b0 error\b",
        r"\bno error\b",
        r"\b0 failure\b",
        r"\bno failure\b",
    ]

    def __init__(
        self,
        default_ok_rc: Optional[set] = None,
        per_tool_validators: Optional[Dict[str, PerToolValidator]] = None,
        crash_log_path: Optional[Path] = Path("hard_fails.log"),
    ) -> None:
        # Which return codes are considered "OK" by default
        self.default_ok_rc = default_ok_rc or {0}
        # Optional: custom validators per tool name (e.g., "ffmpeg")
        self.per_tool_validators = per_tool_validators or {}
        # Where to log crashes / hard failures as BUGs
        self.crash_log_path = crash_log_path

    # ---------- public API ----------

    def check_completed(
        self,
        binary_name: str,
        seed: str,
        cmd: List[str],
        result: subprocess.CompletedProcess,
        expected_outputs: Optional[List[Path]] = None,
    ) -> CommandCheckResult:
        """
        Inspect a completed subprocess result and decide if this run is:
        - OK
        - SOFT_FAIL (invalid/unsupported driver)
        - HARD_FAIL (crash/bug)

        HARD_FAIL events are logged if crash_log_path is set.
        """
        validator = self.per_tool_validators.get(binary_name)
        if validator is not None:
            override = validator(cmd, result)
            if override is not None:
                # If the override says HARD_FAIL, log it
                if override.status is RunStatus.HARD_FAIL:
                    self._log_hard_failure(binary_name, seed, cmd, override)
                return override

        stderr_text = result.stderr.decode(errors="ignore")
        stderr_lower = stderr_text.lower()
        rc = result.returncode

        # ---- 1) Hard failures: treated as BUGs, always logged ----
        if self._matches_any(stderr_lower, self.HARD_FAILURE_PATTERNS):
            res = self._make_result(
                RunStatus.HARD_FAIL, "hard_failure_pattern", rc, stderr_lower
            )
            self._log_hard_failure(binary_name, seed, cmd, res)
            return res

        # ---- 2) Non-zero rc, but may still be usable for profiling ----
        if rc not in self.default_ok_rc:
            if self._matches_any(stderr_lower, self.USAGE_FAILURE_PATTERNS):
                print(stderr_lower)
                return self._make_result(
                    RunStatus.SOFT_FAIL, "usage_error", rc, stderr_lower
                )

            # Generic non-zero rc; for fuzzing this is not fatal
            return self._make_result(
                    RunStatus.OK, "nonzero_rc_but_benign", rc, stderr_lower
                )

        # ---- 3) rc == 0: optionally check for meaningful outputs ----
        if expected_outputs:
            if not self._has_any_nonempty_output(expected_outputs):
                return self._make_result(
                    RunStatus.SOFT_FAIL, "no_nonempty_output_files", rc, stderr_lower
                )

        return self._make_result(RunStatus.OK, "ok", rc, stderr_lower)

    def check_timeout(
        self,
        binary_name: str,
        seed: str,
        cmd: List[str],
        exc: subprocess.TimeoutExpired,
    ) -> CommandCheckResult:
        """
        Helper for callers that catch TimeoutExpired.
        Treats timeouts as HARD_FAIL, and logs them as bugs.
        """
        res = CommandCheckResult(
            status=RunStatus.HARD_FAIL,
            reason=f"timeout_{exc.timeout}s",
            returncode=-1,
            stderr_snippet="",
        )
        self._log_hard_failure(binary_name, seed, cmd, res)
        return res

    # ---------- helpers ----------

    def _matches_any(self, text: str, patterns: List[str]) -> bool:
        return any(re.search(p, text) for p in patterns)

    def _has_any_nonempty_output(self, paths: List[Path]) -> bool:
        for p in paths:
            try:
                if p.exists() and p.stat().st_size > 0:
                    return True
            except OSError:
                continue
        return False

    def _make_result(
        self,
        status: RunStatus,
        reason: str,
        rc: int,
        stderr_lower: str,
        max_len: int = 200,
    ) -> CommandCheckResult:
        snippet = stderr_lower[:max_len].replace("\n", " ")
        return CommandCheckResult(
            status=status,
            reason=reason,
            returncode=rc,
            stderr_snippet=snippet,
        )
    
    def _resolve_symlink(self, link_path: str) -> str:
        """
        Given a soft link path, return the resolved absolute path.
        If the path is not a symlink (shouldn't happen for seeds), return "".
        """
        p = Path(link_path)
        if not p.is_symlink():
            return ""

        resolved_target = os.path.realpath(str(p))
        return resolved_target

    def _log_hard_failure(
        self,
        binary_name: str,
        seed: str,
        cmd: List[str],
        result: CommandCheckResult,
    ) -> None:
        """
        Append a JSON line describing the HARD_FAIL (bug/crash) to crash_log_path.
        Safe to call even if crash_log_path is None.
        """
        if not self.crash_log_path:
            return

        real_seed = self._resolve_symlink(seed)
        try:
            record = {
                "ts": time.time(),
                "binary": binary_name,
                "seed": real_seed,
                "cmd": " ".join(cmd),
                "status": result.status.value,
                "reason": result.reason,
                "returncode": result.returncode,
                "stderr": result.stderr_snippet,
            }
            with self.crash_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            # Logging should never crash the fuzzer / drivergen
            pass
