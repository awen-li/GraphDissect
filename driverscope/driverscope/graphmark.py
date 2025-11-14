import graphmarker
import subprocess
import json
import os

class GraphMark:
    def __init__(self, benchPath, binaryPath):
       self.benchPath  = benchPath
       self.binaryPath = binaryPath

    def loadDriverList(self, drvListPath="drivers/driver_list.json"):
        """
        Parses a driver_list.json file and returns the list of driver names.

        Args:
            json_path (str): Path to the JSON file (e.g., drivers/driver_list.json)

        Returns:
            List[str]: List of driver identifiers
        """
        try:
            listPath = os.path.join(self.benchPath, drvListPath)
            with open(listPath, 'r') as f:
                data = json.load(f)

            if 'drivers' in data and isinstance(data['drivers'], list):
                driver_names = []
                for entry in data['drivers']:
                    if isinstance(entry, dict) and len(entry) == 1:
                        _, value = list(entry.items())[0]
                        driver_names.append(value)
                    else:
                        print(f"[!] Malformed driver entry: {entry}")
                return driver_names
            else:
                raise ValueError(f"Invalid format: 'drivers' list not found in {listPath}")

        except Exception as e:
            print(f"[!] Failed to load driver list: {e}")
            return []

    
    def isCppBinary(self):
        """
        Simplified heuristic: returns True if binary contains vtable symbols,
        indicating C++ class with virtual functions.
        """
        try:
            result = subprocess.run(
                f"nm {self.binaryPath} | grep '_ZTV' | head -n 1",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception as e:
            print(f"[!] Error checking C++ binary: {e}")
            return False

    def extractSymbols(self):
        """
        Extracts (demangled_name, mangled_name) pairs using awk from nm output.

        Returns:
            List of tuples: (demangled_name, mangled_name)
        """
        # Extract demangled symbols using: nm -C <binary>'
        demangledProc = subprocess.run(
            f"nm -C {self.binaryPath}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        demangledLines = demangledProc.stdout.strip().splitlines()

        # Extract mangled symbols using: nm <binary>'
        mangledProc = subprocess.run(
            f"nm {self.binaryPath}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        mangledLines = mangledProc.stdout.strip().splitlines()

        symbolPairs = {}
        for demangled, mangled in zip(demangledLines, mangledLines):
            dem_parts  = demangled.strip().split()
            mang_parts = mangled.strip().split()

            if len(dem_parts) >= 3 and len(mang_parts) >= 3:
                sym_type = dem_parts[1]
                if sym_type not in ('T', 'W'):  # Only keep text symbols (functions)
                    continue

                demangled_symbol = ' '.join(dem_parts[2:])
                mangled_symbol = ' '.join(mang_parts[2:])
                symbolPairs[demangled_symbol] = mangled_symbol
                #print(f"{demangled_symbol} --> {mangled_symbol}")
        
        return symbolPairs


    def markGraph(self):
        symbolPairs = {}
        if self.isCppBinary():
            symbolPairs = self.extractSymbols()
        else:
            print("C-format executable")

        drivers = self.loadDriverList()
        graphmarker.init(self.benchPath)
        graphmarker.markDriver(drivers, symbolPairs)