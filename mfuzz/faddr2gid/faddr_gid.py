import re
import os
import subprocess
from collections import defaultdict
import genfid

##########################################
# nm path
##########################################
# save the correlation between name and addr
# e.g., func1: 0x1234
##########################################
# graph path
##########################################
# save the correlation between name and id
# e.g., func1: 1

class FaddrMap:
    def __init__(self, bench: str, binary: str):
        self.bench_path  = bench
        self.binary_path = os.path.join(bench, binary)

        # Generate function ID map using the C++ extension module
        genfid.genFuncIdMap(bench)

        self.faddr_path = os.path.join(bench, "function_addr.map")
        self.fid_path   = os.path.join(bench, "function_id.map")

        # Patterns to exclude sanitizer / runtime / fuzzing symbols
        self._excluded_patterns = [
            # Sanitizers
            r'.*__sanitizer.*', r'.*__hwasan.*', r'.*__ubsan.*', r'.*__asan.*',
            r'.*__msan.*', r'.*__lsan.*', r'.*__sancov.*',

            # Interceptors / Compiler internals
            r'.*__intercept.*', r'.*__libc_.*', r'.*__llvm.*',

            # Fuzzers
            r'^hfuzz_', r'^honggfuzz_',

            # Init/Fini/runtime sections
            r'_start', r'_init', r'_fini', r'__init_', r'__fini_',
        ]
        self._exclude_re = re.compile('|'.join(self._excluded_patterns))

    # ---- low-level helpers -------------------------------------------------
    def _symbol_allowed(self, name: str) -> bool:
        """Return False if the symbol should be filtered out."""
        return not self._exclude_re.match(name)

    def _parse_nm_text(self, lines):
        """
        Parse lines from `nm -n` output.

        Accepts lines of the form:
            <addr> <type> <name>

        Returns:
            dict[int, str]: addr -> symbol name
        """
        addr_to_func = {}

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 3:
                continue

            addr_str, symbol_type, name = parts[0], parts[1], parts[2]

            if symbol_type.upper() not in ('T', 't', 'W', 'U'):
                continue
            if not self._symbol_allowed(name):
                continue

            try:
                addr = int(addr_str, 16)
            except ValueError:
                continue

            addr_to_func[addr] = name

        return addr_to_func

    # ---- main executable: function_addr.map -------------------------------
    def parseNmOutput(self):
        """
        Run `nm -n` on the main executable and return addr -> name mapping.

        Also writes the raw nm output to function_addr.map for inspection.
        """
        if not os.path.isfile(self.binary_path):
            print(f"[!] binary not found: {self.binary_path}")
            return None

        try:
            proc = subprocess.run(
                ["nm", "-n", self.binary_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except OSError as e:
            print(f"[!] failed to run nm on {self.binary_path}: {e}")
            return None

        if proc.returncode != 0:
            print(f"[!] nm -n {self.binary_path} failed: {proc.stderr.strip()}")
            return None

        # Optional: dump nm output to function_addr.map for debugging
        try:
            with open(self.faddr_path, "w") as f:
                f.write(proc.stdout)
        except OSError as e:
            print(f"[!] failed to write {self.faddr_path}: {e}")

        lines = proc.stdout.splitlines()
        return self._parse_nm_text(lines)

    # ---- dynamic libs: scan *.so* in bench directory ----------------------
    def _iter_shared_objects(self):
        """
        Iterate over shared objects in bench_path.

        Assumption: all dependent libs are copied into this directory.
        We skip symlinks and only use real files to avoid duplicates.
        """
        if not os.path.isdir(self.bench_path):
            return

        for name in os.listdir(self.bench_path):
            full = os.path.join(self.bench_path, name)
            if not os.path.isfile(full):
                continue
            if os.path.islink(full):
                continue
            # Heuristic: anything with ".so" in the name is treated as a DSO
            if ".so" not in name:
                continue
            yield name, full

    def parseNmOutputDSOs(self):
        """
        Runs `nm -n` on each shared object (*.so*) in bench_path and returns:
            list[(module_name, offset, symbol_name)]
        where "offset" is the symbol value in the shared object (relative).
        """
        results = []

        for mod_name, path in self._iter_shared_objects():
            try:
                proc = subprocess.run(
                    ["nm", "-n", path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
            except OSError as e:
                print(f"[!] Failed to run nm on {path}: {e}")
                continue

            if proc.returncode != 0:
                # Non-fatal; just skip this module
                # print(f"[!] nm failed on {path}: {proc.stderr.strip()}")
                continue

            addr_to_func = self._parse_nm_text(proc.stdout.splitlines())
            for off, name in addr_to_func.items():
                results.append((mod_name, off, name))

        return results

    # ---- function_id.map parsing ------------------------------------------
    def loadFuncIdMap(self):
        """
        Loads the function name to ID mapping from `function_id.map`.

        Returns:
            func_to_id:  dict[str, int]
            func_to_ids: dict[str, list[int]] (stripped name -> list of IDs)
        """
        func_to_ids = defaultdict(list)  # for conservative matching
        func_to_id  = {}
        path = self.fid_path
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    name, id_str = line.split(":", 1)

                    try:
                        fid = int(id_str)
                        func_to_id[name] = fid

                        # conservative mapping for names like fft1024.21526 -> fft1024
                        if "." in name:
                            real_name = name.rsplit(".", 1)[0]
                            func_to_ids[real_name].append(fid)
                    except ValueError:
                        continue
        except FileNotFoundError:
            print(f"[!] File not found: {path}")
            return None, None

        return func_to_id, func_to_ids


    def genFddrIdMap(self):
        """
        Generates and writes a mapping from function address to function ID.

        Output format (unified, space-separated):

        - For main executable functions (absolute addresses):
              0xADDR ID

        - For shared-library functions (relative offsets):
              MODULE_NAME 0xOFFSET ID

          where MODULE_NAME matches the filename of the .so,
          and OFFSET is the symbol value reported by nm.

        The file is written to:
            <bench_path>/faddr_id.map
        """
        # 1) Parse nm output for main executable (from function_addr.map)
        addr_to_func = self.parseNmOutput()  # addr -> name
        if addr_to_func is None:
            return None

        # 2) Parse function-id map produced from the callgraph
        func_to_id, func_to_ids = self.loadFuncIdMap()
        if func_to_id is None:
            return None

        # 3) Parse nm output for all DSOs in the same directory
        dso_entries = self.parseNmOutputDSOs()  # list[(module, offset, name)]

        # Aggregate all symbols into a single stream:
        #   (module_name or None, addr_or_offset, name)
        symbols = []

        # main executable: module = None, addresses absolute
        for addr, name in addr_to_func.items():
            symbols.append((None, addr, name))

        # DSOs: module name + relative offset
        for mod, off, name in dso_entries:
            symbols.append((mod, off, name))

        # 4) Resolve names to IDs (conservative matching for clone suffixes)
        processed = set()
        output_entries = []  # list[(module or None, addr_or_off, id)]

        for module, addr, name in symbols:
            # avoid assigning the same ID multiple times to identical name
            # unless we fall back to conservative list
            fid = None

            if name in processed:
                ids = func_to_ids.get(name)
                if ids:
                    fid = ids.pop()
            else:
                fid = func_to_id.get(name)
                if fid is None and "." in name:
                    # try conservative match without suffix (e.g., foo.123 -> foo)
                    base = name.rsplit(".", 1)[0]
                    ids = func_to_ids.get(base)
                    if ids:
                        fid = ids.pop()

            if fid is not None:
                output_entries.append((module, addr, fid))
                processed.add(name)
            else:
                # Debug message only; not fatal
                # For libs, name may not appear in the callgraph; that is fine.
                # print(f"{name}@{addr} is failed to get associated CG node!")
                pass

        print(f"resolved entries: {len(output_entries)} ---- func_to_id size: {len(func_to_id)}")

        # 5) Write unified faddr_id.map
        output_path = os.path.join(self.bench_path, "faddr_id.map")
        with open(output_path, "w") as f:
            # main exe first (module is None), then DSOs (for readability)
            for module, addr, fid in sorted(output_entries, key=lambda x: (x[0] is not None, x[0] or "", x[1])):
                if module is None:
                    # main executable: absolute address
                    f.write(f"{hex(addr)} {fid}\n")
                else:
                    # shared object: module name + relative offset
                    f.write(f"{module} {hex(addr)} {fid}\n")

        return output_path
