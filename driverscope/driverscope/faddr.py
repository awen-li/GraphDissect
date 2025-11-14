import re
import os
from collections import defaultdict

##########################################
# nm path
##########################################
# save the correlation between name and addr
# e.g., func1: ox1234
##########################################
# graph path
##########################################
# save the correlation between name and id
# e.g., func1: 1

class FaddrMap:
    def __init__(self, bench):
        self.bench_path = bench
        self.faddr_path = os.path.join(bench, "function_addr.map")
        self.fid_path   = os.path.join(bench, "function_id.map")

    def parseNmOutput(self):
        """
        Parses the result of `nm -n <binary>` and returns a dictionary
        mapping function namesto addresses, excluding sanitizer/Honggfuzz symbols.
        """
        addr_to_func = {}

        excluded_patterns = [
            # Sanitizers
            r'.*__sanitizer.*', r'.*__hwasan.*', r'.*__ubsan.*', r'.*__asan.*',
            r'.*__msan.*', r'.*__lsan.*', r'.*__sancov.*',

            # Interceptors / Compiler internals
            r'.*__intercept.*', r'.*__libc_.*', r'.*__llvm.*',

            # Fuzzers
            r'^hfuzz_', r'^honggfuzz_',

            # Init/Fini/runtime sections
            r'_start', r'_init', r'_fini', r'__init_', r'__fini_'
        ]

        exclude_re = re.compile('|'.join(excluded_patterns))

        try:
            with open(self.faddr_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 3:
                        continue

                    addr_str, symbol_type, name = parts
                    if symbol_type.upper() not in ('T', 't', 'W', 'U'):
                        continue

                    if exclude_re.match(name):
                        #print(f"!!! {name} is filtered by regex." )
                        continue

                    try:
                        addr = int(addr_str, 16)
                        addr_to_func[addr] = name
                    except ValueError:
                        continue
        except FileNotFoundError:
            print(f"[!] File not found: {self.faddr_path}")
            return None

        return addr_to_func

    def loadFuncIdMap(self):
        """
        Loads the function name to ID mapping from the `graph_path` file.

        Returns:
            dict[str, int]: Mapping from function name to unique ID.
        """
        func_to_ids = defaultdict(list) # for conservative coputation: fft1024.21526 & fft1024 --> fft1024
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
                        func_to_id[name] = int(id_str)

                        if "." in name:
                            real_name = name.rsplit(".")[0]
                            func_to_ids[real_name].append (int(id_str))

                    except ValueError:
                        continue
        except FileNotFoundError:
            print(f"[!] File not found: {path}")
            return None
        
        return func_to_id, func_to_ids

    def genFddrIdMap(self):
        """
        Generates and writes a mapping from function address to function ID.
        Output is written to 'function_id.map' in format: <addr_hex>:<id>
        """
        addr_to_func = self.parseNmOutput()  # name → addr
        if addr_to_func == None:
            return None
        
        func_to_id, func_to_ids = self.loadFuncIdMap()   # name → id
        if func_to_id == None:
            return None

        addr_to_id = {}
        processed  = []
        for addr, name in addr_to_func.items():
            if name in processed:
                ids = func_to_ids.get(name)
                if ids != None and len (ids) != 0:
                    func_id = ids.pop()
                    addr_to_id[addr] = func_id
                    continue
            
            id = func_to_id.get(name)
            if id != None:
                addr_to_id[addr] = id
                if not name in processed:
                    processed.append (name)
                continue
            print(f"{name}@{addr} is failed to get associated CG node!")
        print (f"addr_to_id size: {len(addr_to_id)} ---- func_to_id size:{len(func_to_id)}")

        # Write to function_id.map
        output_path = os.path.join(self.bench_path, "faddr_id.map")
        with open(output_path, "w") as f:
            for addr, id in sorted(addr_to_id.items()):
                f.write(f"{hex(addr)}:{id}\n")  # address in hex
        
        return


