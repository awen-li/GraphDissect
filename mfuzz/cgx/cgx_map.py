import os
import re
from collections import defaultdict
import subprocess
from tqdm import tqdm
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
        self.functions = cgxmarker.getAllFunctions()

    def update_cgmap(self):
        # parse functions
        print("CGX: parsing functions...")
        self.parse_functions(self.functions)

        # parse callsites
        print("CGX: parsing callsites...")
        self.parse_callsites(self.functions)

        # dump graph
        print("CGX: dumping graph...")
        cgxmarker.dumpGraph()
        return True

    def parse_functions(self, functions):
        """
        Parse function addresses using `nm` and set node keys for functions in functions.
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
        for fn in functions:
            fname = fn
            if "." in fn:
                fname = fn.rsplit(".", 1)[0]

            addr = name2addr.get(fname)
            if addr is None:
                continue

            cgxmarker.setNodeKey(fn, addr)

        return

    def parse_callsites(self, functions):
        funcs = list(functions)
        for fn in tqdm(funcs, desc="Parsing callsites", unit="func"):
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
                if callee in functions:
                    direct_callees.add(callee)
                    cgxmarker.setEdgeKey(fn, callee, retsite)

            # conservative mapping for indirect sites
            all_callees = cgxmarker.getCallees(fn)
            for callee in (set(all_callees) - direct_callees):
                for retsite in indirect_retsites:
                    cgxmarker.setEdgeKey(fn, callee, retsite)
        