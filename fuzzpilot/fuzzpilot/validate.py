import os
import json
import shlex
import shutil
import time
import subprocess as sp
from typing import Dict, Any, List, Optional, Tuple, Set


class Validator:
    def __init__(self, bench_path: str, exe_list: List[str]):
        """
        bench_path: root path that contains <exe>/drivers and <exe>/fuzz/out
        exe_list:   list of executable names to process, e.g. ["exiv2"]
        """
        self.bench_path   = os.path.abspath(bench_path)
        self.all_exes     = list(exe_list)
        self.abnormal_dir = os.path.join(self.bench_path, "abnormal")
        self.common_failed_corpus: Set[str] = set()

    # ---------- discovery ----------
    def discover_drivers(self, exe_name: str) -> Dict[str, Dict[str, str]]:
        """
        Returns: { driver_label: {"profile": <path or None>, "binary": <path or None>, "corpus": <dir>} }
        """
        exe_dir = os.path.join(self.bench_path, exe_name, "drivers")
        drivers: Dict[str, Dict[str, str]] = {}
        if not os.path.isdir(exe_dir):
            return drivers

        for entry in sorted(os.listdir(exe_dir)):
            dpath = os.path.join(exe_dir, entry)
            if not os.path.isdir(dpath):
                continue

            profile_json = os.path.join(dpath, f"{entry}.json")
            binary_path = self._first_executable(dpath)
            corpus_path = os.path.join(self.bench_path, exe_name, "fuzz", "out", entry)

            drivers[entry] = {
                "profile": profile_json if os.path.isfile(profile_json) else None,
                "binary": binary_path,
                "corpus": corpus_path,
                "exe": exe_name,
                "label": entry,
            }
        return drivers

    @staticmethod
    def _first_executable(d: str) -> Optional[str]:
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None

    # ---------- profile & cmd ----------
    @staticmethod
    def _load_profile(path: Optional[str]) -> Dict[str, Any]:
        if not path or not os.path.isfile(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _normalize_args(args_field):
        """
        Accepts: "-e - adjust"  OR  ["-e - adjust"]  OR  ["-e", "-", "adjust"]
        Produces: ["-e", "-", "adjust"]
        """
        def _split(s):
            s = s.strip()
            if not s:
                return []
            try:
                return shlex.split(s)
            except ValueError as e:
                print(f"[warn] shlex error in args item {s!r}: {e}. Falling back to simple split.", flush=True)
                return s.split()

        if not args_field:
            return []

        if isinstance(args_field, str):
            return _split(args_field)

        if isinstance(args_field, list):
            out = []
            for item in args_field:
                if item is None:
                    continue
                if isinstance(item, str):
                    out.extend(_split(item))
                else:
                    out.append(str(item))
            return out

        # Fallback for scalars (int/float/bool)
        return [str(args_field)]

    def _build_cmd(
        self, binary: str, profile: Dict[str, Any], seed_path: str
    ) -> Tuple[List[str], Optional[bytes], Dict[str, str], Set[int]]:
        args = self._normalize_args(profile.get("args"))
        use_stdin = bool(profile.get("stdin", False))

        # Replace @@ with seed path if present; otherwise append (unless using stdin)
        if any(a == "@@" for a in args):
            args = [seed_path if a == "@@" else a for a in args]
        elif not use_stdin:
            args = args + [seed_path]

        # Environment and allowed exits
        env = dict(os.environ)
        if isinstance(profile.get("env"), dict):
            env.update({str(k): str(v) for k, v in profile["env"].items()})

        ok_exits: Set[int] = {0}
        if isinstance(profile.get("ok_exits"), list):
            for x in profile["ok_exits"]:
                try:
                    ok_exits.add(int(x))
                except Exception:
                    pass

        stdin_bytes = None
        if use_stdin:
            try:
                with open(seed_path, "rb") as f:
                    stdin_bytes = f.read()
            except Exception:
                stdin_bytes = b""

        return [binary] + args, stdin_bytes, env, ok_exits

    # ---------- execution ----------
    @staticmethod
    def _decode(b: Optional[bytes]) -> str:
        if not b:
            return ""
        for enc in ("utf-8", "latin-1", "utf-16-le", "utf-16-be"):
            try:
                return b.decode(enc, errors="ignore")
            except Exception:
                pass
        return ""

    def _exec(self, argv, stdin_bytes, env, timeout, ok_exits):
        start = time.time()
        try:
            cp = sp.run(argv, input=stdin_bytes,
                        stdout=sp.PIPE, stderr=sp.PIPE,
                        env=env, timeout=timeout, check=False)
            dur_ms = int((time.time() - start) * 1000)
        except sp.TimeoutExpired as te:
            dur_ms = int((time.time() - start) * 1000)
            return (-1, "TIMEOUT", dur_ms, self._decode(getattr(te, "stderr", b"")))

        rc = cp.returncode
        stderr_txt = self._decode(cp.stderr)

        if rc < 0:          # killed by signal
            status = "CRASH"
        elif rc in ok_exits:
            status = "OK"
        else:
            status = "NONZERO"

        return (rc, status, dur_ms, stderr_txt[:200].strip())
    

    def _write_abnormal(self, exe: str, label: str, seed_path: str,
                        argv: List[str], rc: int, status: str, dur_ms: int, stderr_snip: str) -> None:
        """
        Write a concise result file for abnormal executions and copy the offending seed.
        Files:
        <abnormal_dir>/<exe>/<label>/<seed>.txt
        <abnormal_dir>/<exe>/<label>/<seed>
        """
        out_dir = os.path.join(self.abnormal_dir, exe, label)
        os.makedirs(out_dir, exist_ok=True)

        base = os.path.basename(seed_path)
        log_path = os.path.join(out_dir, f"{base}.txt")
        seed_copy_path = os.path.join(out_dir, base)

        try:
            # write log
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"status: {status}\n")
                f.write(f"exit_code: {rc}\n")
                f.write(f"duration_ms: {dur_ms}\n")
                f.write(f"cmd: {shlex.join(argv)}\n")
                if stderr_snip:
                    f.write("\nstderr:\n")
                    f.write(stderr_snip)

            # copy the exact seed bytes next to the log
            if os.path.isfile(seed_path):
                shutil.copyfile(seed_path, seed_copy_path)

        except Exception as e:
            print(f"[warn] failed to write abnormal artifacts for {seed_path}: {e}")

    # ---------- common failed corpus ----------
    def get_common_failed_corpus(self, exe_path: str) -> Set[str]:
        """
        Return all *.fuzz files in the same directory as exe_path.
        Uses os.scandir() to handle very large directories efficiently.
        """
        common_failed: Set[str] = set()
        exe_dir = os.path.abspath(exe_path)

        if not os.path.isdir(exe_dir):
            return common_failed

        with os.scandir(exe_dir) as it:
            for entry in it:
                if entry.is_file() and entry.name.endswith(".fuzz"):
                    common_failed.add(entry.path)

        return common_failed

    # ---------- run ----------
    def run_driver(self, driver_info: Dict[str, str], timeout: float = 10.0):
        """
        Execute the driver's binary over all files in its fuzzed corpus directory.
        Prints concise results.
        """
        binary = driver_info.get("exe")
        if not binary:
            print(f"!!!![skip] binary missing: driver_info={driver_info}")
            return
        
        binary_path = os.path.join(self.bench_path, binary, binary)
        if not os.path.exists(binary_path):
            print(f"!!!![skip] binary missing: driver_info={binary_path}")
            return
        
        corpus = driver_info.get("corpus")
        if not os.path.isdir(corpus):
            print(f"!!!![skip] corpus missing: binary={binary}")
            return
        
        profile_path = driver_info.get("profile")
        profile = self._load_profile(profile_path)

        # flat corpus dir: every file is a seed
        seeds = [
            os.path.join(corpus, f)
            for f in sorted(os.listdir(corpus))
            if os.path.isfile(os.path.join(corpus, f))
        ] + list(self.common_failed_corpus) 
        
        if not seeds:
            print(f"[warn] empty corpus: {corpus}")
            return

        for spath in seeds:
            argv, stdin_bytes, env, ok_exits = self._build_cmd(binary_path, profile, spath)
            rc, status, ms, err_snip = self._exec(argv, stdin_bytes, env, timeout, ok_exits)
            print(f"[{status}] rc={rc} {os.path.basename(binary)} {os.path.basename(spath)} ({ms}ms)")

            ABNORMAL_STATUSES = {"CRASH", "TIMEOUT"}
            # save artifacts if abnormal
            if status in ABNORMAL_STATUSES:
                exe   = driver_info.get("exe", "exe")
                label = driver_info.get("label", "driver")
                self._write_abnormal(exe, label, spath, argv, rc, status, ms, err_snip)

    # ---------- run all ----------
    def run_all(self, timeout: float = 10.0):
        """
        Discover and run every driver for every exe in self.all_exes.
        """
        for exe in self.all_exes:
            fuzz_ir = os.path.join(self.bench_path, exe, "fuzz")
            if not os.path.exists(fuzz_ir):
                print(f"!!!![skip] fuzz directory missing: driver_info={self.bench_path}-{exe}")
                return

            self.common_failed_corpus = self.get_common_failed_corpus(
                os.path.join(self.bench_path, exe)
            )
        
            print(f"run_all --> {exe}")
            drivers = self.discover_drivers(exe)
            if not drivers:
                print(f"[info] no drivers for {exe}")
                continue
            print(f"[info] running {len(drivers)} drivers for {exe}")

            for label, info in drivers.items():
                self.run_driver(info, timeout=timeout)
