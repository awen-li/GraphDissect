import os
import re
from collections import defaultdict
import subprocess
import cgxmarker

CALL_RE = re.compile(
    r'^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)\s+call\w*\s+(.*)$'
)

SYM_RE = re.compile(r'<([^>]+)>')  # extract foo from "<foo>"

def disasm_function(binary_path: str, func_name: str) -> str:
    cmd = ["llvm-objdump", "-d", "--symbolize-operands", f"--disassemble-symbols={func_name}", binary_path]
    return subprocess.check_output(cmd, text=True, errors="ignore")

def parse_callsites_from_objdump(text: str):
    """
    Yield tuples: (callee_name_or_none, retsite_int)
    """
    for line in text.splitlines():
        m = CALL_RE.match(line)
        if not m:
            continue
        addr_hex, bytes_str, tail = m.group(1), m.group(2), m.group(3)
        callsite = int(addr_hex, 16)

        # count bytes to get instruction size
        nbytes = len(bytes_str.split())
        retsite = callsite + nbytes

        # try to extract callee symbol name: "... <callee>"
        sm = SYM_RE.search(tail)
        callee = sm.group(1) if sm else None

        yield callee, retsite


class CgxMap:
    def __init__(self, bench: str, binary: str):
        self.bench_path  = bench
        self.binary_path = os.path.join(bench, binary)
        cgxmarker.initMarker(self.bench_path)

    def update_cgmap(self):
        func_to_id, func_to_ids = self.load_function_id_map()
        if func_to_id is None:
            return None

        # parse functions
        self.parse_functions(func_to_id)

        # parse callsites
        self.parse_callsites(func_to_id)

        # dump graph
        cgxmarker.dumpGraph()
        return True

    def parse_functions(self, func_to_id):
        """
        Parse function addresses using `nm` and set node keys for functions in func_to_id.
        Assumes non-stripped binary.
        """
        # nm output: "00000000004010b0 T foo"
        cmd = ["nm", "-n", "--defined-only", self.binary_path]
        out = subprocess.check_output(cmd, text=True, errors="ignore")

        # build name -> addr (hex int)
        name2addr = {}
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            addr_hex, sym_type, name = parts[0], parts[1], parts[2]

            # only keep text/code symbols (T/t/W/w are common for functions)
            if sym_type not in ("T", "t", "W", "w"):
                continue

            try:
                addr = int(addr_hex, 16)
            except ValueError:
                continue
            name2addr[name] = addr

        # update node keys only for functions in callgraph
        for fn in func_to_id.keys():
            fname = fn
            if "." in fn:
                fname = fn.rsplit(".", 1)[0]

            addr = name2addr.get(fname)
            if addr is None:
                continue
            
            cgxmarker.setNodeKey(fn, addr)

        return

    def parse_callsites(self, func_to_id):
        for fn in func_to_id.keys():
            fname = fn
            if "." in fn:
                fname = fn.rsplit(".", 1)[0]
            
            try:
                text = disasm_function(self.binary_path, fname)
            except subprocess.CalledProcessError:
                continue

            direct_callees = set()
            indirect_retsites = set()

            for callee, retsite in parse_callsites_from_objdump(text):
                if callee is None:
                    indirect_retsites.add(retsite)
                    continue

                # Only keep callees that are in your callgraph set
                if callee in func_to_id:
                    direct_callees.add(callee)
                    cgxmarker.setEdgeKey(fn, callee, retsite)

            # conservative mapping for indirect sites
            all_callees = cgxmarker.getCallees(fn)
            for callee in (set(all_callees) - direct_callees):
                for retsite in indirect_retsites:
                    cgxmarker.setEdgeKey(fn, callee, retsite)
        

    def load_function_id_map(self):
        """
        Loads the function name to ID mapping from `function_id.map`.

        Returns:
            func_to_id:  dict[str, int]
            func_to_ids: dict[str, list[int]] (stripped name -> list of IDs)
        """
        func_to_ids = defaultdict(list)
        func_to_id  = {}

        path = os.path.join(self.bench_path, "function_id.map")
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