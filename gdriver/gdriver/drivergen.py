import os
import re
import json
import copy
import shutil
import random
import string
import subprocess
from typing import List, Any, Optional, Sequence, Tuple
from itertools import combinations, product
from .option import Option
from .binary import Binary
from .profile import IOSpec
from .run_checker import RunChecker, RunStatus

class Driver:
    def __init__(
        self,
        id: int,
        driver: str,
        args: List[str],
        base_args: List[str],
        seed_dir: str = "seeds",
        output: str = "",
        io: IOSpec = None,
        priority: float = 1.0,
        in_place_editing: bool = False,
        description: str = "",
    ):
        self.id = id
        self.driver = driver
        self.args = args
        self.base_args = base_args
        self.seed_dir = seed_dir
        self.io = io if io is not None else IOSpec()
        self.output = output
        self.priority = priority
        self.in_place_editing = in_place_editing
        self.description = description
        self.name = self._build_name()

        # IO formalize
        self._form_input()
        self._form_output()

    def _build_name(self) -> str:
        """
        Build a stable, human-readable name from the arg string/list.

        Examples:
          args = "-C auto"                     -> "id_C_auto"
          args = "-C auto -p file-start"       -> "id_C_auto_p_file_start"
          args = "-x x_file-start-context"     -> "id_x_x_file_start_context"
        """
        if isinstance(self.args, str):
            tokens = self.args.split()
        else:
            tokens = list(self.args)

        parts = []
        for tok in tokens:
            norm = self._normalize_token(tok)
            if norm:
                parts.append(norm)

        if not parts:
            return f"{self.id}_default"

        return f"{self.id}_" + "_".join(parts)

    def _normalize_token(self, tok: str) -> str:
        # Drop leading '-' (flags)
        tok = tok.lstrip("-")
        if not tok:
            return ""

        # Replace any non-alphanumeric with '_'
        tok = re.sub(r"[^0-9A-Za-z]", "_", tok)
        # Collapse multiple '_' and strip edges
        tok = re.sub(r"_+", "_", tok).strip("_")
        return tok

    # ---------- Seeds ----------

    def get_seeds(self, seed_dir, prefix="seed") -> List[str]:
        """
        Return a list of full paths to seed files in the given directory, sorted by seed number.

        Parameters:
            seed_dir (str): Directory containing seed files.
            prefix (str): Prefix of seed files (default: 'seed').

        Returns:
            List[str]: Sorted list of full paths to seed files.
        """
        if not os.path.exists(seed_dir):
            return []

        files = [f for f in os.listdir(seed_dir) if f.startswith(prefix)]
        # Sort by numeric suffix (e.g., seed1, seed2, ..., seed10)
        files.sort(key=lambda x: int("".join(filter(str.isdigit, x)) or 0))
        return [os.path.join(seed_dir, f) for f in files]

    # ---------- Args flattening ----------
    def flatten_args(self) -> List[str]:
        """
        Turn self.args (which may be a list of chunks like
        ["-a -b elf64-x86-64"] or ["-a", "-b elf64-x86-64"])
        into real argv tokens: ["-a", "-b", "elf64-x86-64"].
        """
        if isinstance(self.args, str):
            return self.args.split()

        args: List[str] = []
        for a in self.args:
            if a in ("", None):
                continue
            # each chunk may contain spaces, e.g. "-c auto", "-a -b elf64-x86-64"
            args.extend(str(a).split())
        return args

    # ---------- IO construction ----------
    def _form_input(self) -> None:
        """
        Normalize input into args according to IO spec.

        For flagged input:
          - append the flag to args, but NOT the seed (seed is added in build_cmd).
        For positional input:
          - do nothing here; seed will be appended directly.
        """
        if self.io.input.kind == "flagged":
            if not self.io.input.flag:
                raise ValueError("flagged input requires a non-empty flag")
            self.args.append(self.io.input.flag)
        # positional → no change

    def _form_output(self) -> None:
        """
        Normalize output string according to IO spec.

        For flagged output:
          - store "flag value" as a single string in self.output
            so it shows up like "-o out" in the driver spec.
        For positional output:
          - leave self.output unchanged.
        """
        if not self.output:
            return

        if self.io.output.kind == "flagged":
            if not self.io.output.flag:
                raise ValueError("flagged output requires a non-empty flag")
            # keep the combined form for the driver spec
            self.output = f"{self.io.output.flag} {self.output}"

    def build_cmd(self, binary_path: str, seed: str) -> List[str]:
        """
        Construct the full command line for this driver and a given seed.
        """
        binary = os.path.join(binary_path, self.driver)
        cmd: List[str] = [binary]

        # base args
        cmd += self.base_args

        # static args
        cmd += self.flatten_args()

        # input seed (positional; input flag already in args if needed)
        cmd += [seed]

        # output: may be "out" or "-o out"
        if self.output:
            # IMPORTANT: split here so "-o out" becomes ["-o", "out"]
            cmd += str(self.output).split()
        
        return cmd

    # ---------- Calibration ----------
    def safe_remove(self, path: str):
        try:
            os.remove(path)
        except Exception:
            pass

    def calibrate(self, binary_path: str, seed_list: List[str]) -> bool:
        """
        Test if this driver configuration can run standalone (without crashing or critical failure).

        Args:
            binary_path: Directory containing the target binary.
            seed_list: List of input seed file paths.

        Returns:
            True if the driver appears valid (some seeds worked), False otherwise.
        """
        checker = RunChecker()
        failed = 0
        for seed in seed_list:
            cmd = self.build_cmd(binary_path, seed)
            #print(f"[calibrate]{self.driver} --> {cmd}")

            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                )

                check_result = checker.check_completed(self.driver, seed, cmd, result)
                if check_result.status is not RunStatus.OK:
                    print(f"@calibrate: \t{' '.join(cmd)} --> {check_result.status.value}: {check_result.reason}")
                    failed += 1
                    self.safe_remove(seed)
            except subprocess.TimeoutExpired as e:
                check = checker.check_timeout(self.driver, seed, cmd, e)
                print(f"@calibrate: \t{' '.join(cmd)} --> {check.status.value}: {check.reason}")
                failed += 1
                self.safe_remove(seed)
            except Exception as e:
                print(f"Exception while testing {cmd}: {e}")
                failed += 1
                self.safe_remove(seed)

        print(f"[calibrate]{self.driver} --> failed = {failed}/{len(seed_list)}")
        return failed < len(seed_list)

    # ---------- Serialization ----------

    def to_json(self):
        driver_json = {
            "id": self.id,
            "name": self.name,
            "driver": self.driver,
            "args": self.base_args + self.args,
            "seed_dir": self.seed_dir,
            "output": self.output,
            "priority": self.priority,
            "description": self.description,
        }

        if self.in_place_editing:
            driver_json["in_place_editing"] = 1

        return driver_json


class DriverGenerator:
    def __init__(self, binary_path: str):
        """
        binary_path: actual path to the binary (e.g., /home/binutils/objdump)
        binary: Binary profile object loaded from YAML (objdump.yaml)
        """
        self.binary_path    = binary_path
        self.output_path    = os.path.join(binary_path, "drivers")
        self.max_seeds_num  = 1024

        self.binary = Binary (binary_path)
        if not self.binary.primary_options:
            raise ValueError(f"No primary options found for binary: {binary_path}")
        #self.binary.debug_print()

        self.binary_name    = self.binary.get_binary_name()

    def get_driver_root(self, driver: Driver) -> str:
        return driver.name

    def checkCached(self) -> bool:
        driver_list_path = os.path.join(self.output_path, "driver_list.json")
        if not os.path.exists(driver_list_path):
            return False

        with open(driver_list_path, "r") as f:
            driver_list_obj = json.load(f)
        
        expected_num = len(driver_list_obj.get("drivers", []))
        if expected_num == 0:
            return False

        actual_num = 0
        for d in driver_list_obj.get("drivers", []):
            for driver_id, driver_name in d.items():
                driver_path = os.path.join(self.output_path, driver_name)
                driver_json_path = os.path.join(driver_path, f"{driver_name}.json")
                if os.path.exists (driver_json_path):
                    actual_num += 1

        print(f"[+] Cached drivers found: expected {expected_num}, actual {actual_num}")
        return expected_num == actual_num
    
    def cleanup_seeds(self, driver: Driver):
        """
        Remove all non-symlink files from a seeds/ directory.

        Assumptions:
        - All real seeds are symlinks.
        - Any regular file in this directory is garbage (e.g., seed0.exv copied by calibration).

        """
        seed_dir = os.path.join(self.output_path, self.get_driver_root(driver), "seeds")
        if not os.path.isdir(seed_dir):
            return

        for name in os.listdir(seed_dir):
            path = os.path.join(seed_dir, name)
            # Only kill things that are NOT symlinks
            if not os.path.islink(path):
                driver.safe_remove(path)
        return

    def gen_seed(self, driver: Driver) -> List[str]:
        """
        Generate or copy seeds for a given driver.

        For each file under <binary_path>/seeds, create a seedN symlink under
        <output_path>/<driver_root>/seeds, pointing to the file via an absolute path.
        Then return at most max_seeds_num seed paths as seen by driver.get_seeds().
        """
        # Where this driver's seeds will live
        seed_path = os.path.join(self.output_path, self.get_driver_root(driver), "seeds")
        os.makedirs(seed_path, exist_ok=True)

        # Global seed directory for this binary
        initial_seeds_dir = os.path.join(self.binary_path, "seeds")

        if os.path.isdir(initial_seeds_dir):
            seed_no = 0
            # Sort for determinism
            for f in sorted(os.listdir(initial_seeds_dir)):
                src = os.path.join(initial_seeds_dir, f)
                # Only link regular files
                if not os.path.isfile(src):
                    continue

                # Use absolute path for the symlink target
                src_abs = os.path.abspath(src)
                dst = os.path.join(seed_path, f"seed{seed_no}")
                seed_no += 1

                # If a link/file already exists there, skip (do not overwrite)
                if os.path.exists(dst) or os.path.islink(dst):
                    continue

                try:
                    os.symlink(src_abs, dst)
                    # print(f"@gen_seed link {src_abs} -> {dst} succeeded")
                except FileExistsError:
                    # print(f"[!] Link already exists: {dst}")
                    pass
                except OSError as e:
                    print(f"[!] Failed to link {src_abs} -> {dst}: {e}")

        # Let the Driver decide how to enumerate/interpret seeds
        all_seeds = driver.get_seeds(seed_path)

        if len(all_seeds) > self.max_seeds_num:
            seed_list = all_seeds[:self.max_seeds_num]
        else:
            seed_list = all_seeds

        return seed_list

    
    def remover_driver(self, driver: Driver) -> None:
        driver_path = os.path.join(self.output_path, self.get_driver_root(driver))
        if os.path.exists(driver_path):
            try:
                shutil.rmtree(driver_path)
            except Exception:
                pass
    
    def gen_driver_list(self, drivers: List[Driver]) -> None:
        driver_list_path = os.path.join(self.output_path, "driver_list.json")
        driver_dict_list = [{d.id: d.name} for d in drivers]
        driver_list_obj = {
            "number": len(driver_dict_list),
            "drivers": driver_dict_list
        }
        with open(driver_list_path, "w") as f:
            json.dump(driver_list_obj, f, indent=4)
        print(f"[+] Generated {len(driver_dict_list)} drivers at: {driver_list_path}")
    
    def write_driver(self, driver: Driver) -> None:
        driver_name = self.get_driver_root(driver)
        driver_path = os.path.join(self.output_path, driver_name)
        os.makedirs(driver_path, exist_ok=True)
        with open(os.path.join(driver_path, f"{driver_name}.json"), "w") as f:
            json.dump(driver.to_json(), f, indent=4)


    def build_args_for_option(self, opt: Option) -> List[str]:
        """
        Turn a Option objects into a list of *atomic* argument strings.

        - Normal option:
            flag only         -> ["-p"]
            flag + arg        -> ["-p pretty"]

        - Choice option (kind == "choice"):
            expand all choices:
                "-C" with choices ["auto", "gnu-v3", "java"]
                -> ["-C auto", "-C gnu-v3", "-C java"]
        """
        args: List[str] = []

        kind = getattr(opt, "kind", None)
        flag = opt.option

        # Choice options: emit one "<flag> <value>" per choice
        if kind == "choice":
            choices = getattr(opt, "choices", [])
            print(f"  [build_args_for_option] expanding choice option {flag} with choices: {choices}")
            for val in choices:
                args.append(f"{flag} {val}")
            print(f"    -> {args}")
        elif kind == "value":
            # Value options: emit one "<flag> <value>" for the default value(s)
            defaults = getattr(opt, "defaults", [])
            print(f"  [build_args_for_option] expanding value option {flag} with defaults: {defaults}")
            for val in defaults:
                args.append(f"{flag} {val}")
            print(f"    -> {args}")
        elif kind == "default":
            # default driver
            args.append("")
        else:
            # Default: single option, maybe with one argument
            arg = getattr(opt, "arg", None)
            if arg not in (None, ""):
                args.append(f"{flag} {arg}")
            else:
                args.append(flag)
        
        return args

    def build_args_for_combinations(self, opts_list: Sequence["Option"]) -> List[str]:
        """
        Build all concrete argument *strings* for a given list of options.
        This function then performs a Cartesian product over these per-option lists,
        selecting exactly one string for each option and concatenating them into a
        single argument string for a driver. For example:

            opts_list = [ -a,  -c{auto, gnu-v3},  -z ]
            build_args_for_option(-a)           -> ["-a"]
            build_args_for_option(-c, choices)  -> ["-c auto", "-c gnu-v3"]
            build_args_for_option(-z)           -> ["-z"]

            => args_list_list = [
                ["-a"],
                ["-c auto", "-c gnu-v3"],
                ["-z"],
            ]

            Cartesian product over args_list_list yields:
                ("-a", "-c auto", "-z")
                ("-a", "-c gnu-v3", "-z")

            which are joined into final strings:
                "-a -c auto -z"
                "-a -c gnu-v3 -z"

        Returns:
            A list of argument strings, where each string corresponds to one
            concrete combination of the given options. The caller is responsible
            for controlling how many options are included (e.g., primary + 1
            secondary, primary + 2 secondaries, etc.), and for bounding the
            combinatorial explosion.
        """
        args_list_list: List[List[str]] = []
        for o in opts_list:
            arg_chunks = self.build_args_for_option(o)
            print (f"build_args_for_option({o.option}) -> {arg_chunks}")
            if arg_chunks:
                args_list_list.append(arg_chunks)

        if not args_list_list:
            return []

        final_args_list: List[str] = []
        for combo in product(*args_list_list):
            # combo is a tuple of strings like ("-a", "-c auto", "-z")
            final_args = " ".join(combo)
            final_args_list.append(final_args)

        return final_args_list

    def gen_all_secondary_combos(self,
                                 primary: Option,
                                 secondaries: Sequence[Option],
                                 k: int) -> List[Tuple[Sequence[Option], str]]:
        """
        Generate all argument strings for a given primary option combined with
        exactly `k` secondary options.

        Returns:
            List of (secondary_subset, arg_string) pairs.
        """
        results: List[Tuple[Sequence[Option], str]] = []

        if k <= 0 or not secondaries:
            return results

        for subset in combinations(secondaries, k):
            opts_list = [primary] + list(subset)
            combo_args = self.build_args_for_combinations(opts_list)
            for arg_str in combo_args:
                results.append((subset, arg_str))

        return results
    
    def select_output(self, primary_opt: Option, second_opts: List[Option]) -> str:
        if primary_opt.output != "":
            return primary_opt.output
        
        for opt in second_opts:
            if opt.output != "":
                return opt.output
        return ""

    # ------------------------------------------------------------------
    # Main generation using Binary profile
    # ------------------------------------------------------------------
    def generate(self) -> bool:
        """
        Logic:
          1. Generate drivers with all primary options (each atomic primary,
             including each choice value, becomes a separate driver).
          2. Following max_combination, combine primary + secondary options
             (up to max_combination-1 secondaries), respecting constraints.
        """
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")
        os.makedirs(self.output_path, exist_ok=True)

        driver_id = 1
        drivers: List[Driver] = []

        max_combination = self.binary.profile.max_combination
        max_secondary = max(0, max_combination - 1)

        # -------------------------------------------------
        # Step 1: primary-only drivers
        # -------------------------------------------------
        for primary_opt in self.binary.primary_options:
            print(f"\n\n[generation] primary-only driver [{driver_id}] "
                  f"for option: {primary_opt.option} {primary_opt.arg}")

             # e.g. ["-C auto", "-C gnu-v3", "-C java"]
            primary_chunks = self.build_args_for_option(primary_opt)

            for chunck in primary_chunks:
                args_list = [chunck]
                driver = Driver(
                    id=driver_id,
                    driver=self.binary_name,
                    args=args_list,
                    base_args=self.binary.profile.base_args,
                    seed_dir="seeds",
                    output=self.select_output(primary_opt, []),
                    io=self.binary.profile.io,
                    priority=1.0,
                    in_place_editing=getattr(primary_opt, "in_place_editing", False),
                    description=primary_opt.description
                )

                seed_list = self.gen_seed(driver)
                success = driver.calibrate(self.binary_path, seed_list)

                if not success:
                    self.remover_driver(driver)
                    continue
                
                self.cleanup_seeds(driver)
                drivers.append(driver)
                self.write_driver(driver)
                driver_id += 1
                print(driver.to_json())

        # -------------------------------------------------
        # Step 2: primary + secondary combinations
        # -------------------------------------------------
        if max_secondary > 0 and self.binary.second_options:
            for primary_opt in self.binary.primary_options:
                for k in range(1, max_secondary + 1):
                    combo_entries = self.gen_all_secondary_combos(primary_opt,
                                                                  self.binary.second_options,
                                                                  k=k)
                    for sec_subset, arg_str in combo_entries:
                        args_list = [arg_str]

                        description = " + ".join(
                            [primary_opt.description]
                            + [s.description for s in sec_subset if getattr(s, "description", "")]
                        )

                        editing_flag = getattr(primary_opt, "in_place_editing", False) or any(
                            getattr(s, "in_place_editing", False) for s in sec_subset
                        )

                        print(f"\n\n[generation] primary+{k}-secondary driver "
                              f"[{driver_id}] args: {args_list} ---- editing_flag={editing_flag}") 

                        driver = Driver(
                                    id=driver_id,
                                    driver=self.binary_name,
                                    args=args_list,
                                    base_args=self.binary.profile.base_args,
                                    seed_dir="seeds",
                                    output=self.select_output(primary_opt, sec_subset),
                                    io=self.binary.profile.io,
                                    priority=1.0,
                                    in_place_editing=editing_flag,
                                    description=description,
                                )

                        seed_list = self.gen_seed(driver)
                        success = driver.calibrate(self.binary_path, seed_list)

                        if not success:
                            self.remover_driver(driver)
                            continue
                        
                        self.cleanup_seeds(driver)
                        drivers.append(driver)
                        self.write_driver(driver)
                        driver_id += 1

        self.gen_driver_list(drivers)
        return True
    
    def _flatten_args(self, args) -> List[str]:
        """
        Flatten the 'args' field as stored in the driver JSON into
        atomic argv tokens.

        We intentionally do NOT re-run Driver.__init__ here, to avoid
        re-applying IO normalization (flags would be duplicated).
        """
        if isinstance(args, str):
            return args.split()

        out: List[str] = []
        for a in args:
            if a in ("", None):
                continue
            out.extend(str(a).split())
        return out

    def dump_driver_cmdlines(
        self,
        seed_placeholder: str = "@@",
        out_path: Optional[str] = None,
    ) -> List[Tuple[int, str]]:
        """
        Collect reconstructed command line templates for all drivers of this binary
        and dump them to a text file.

        Each line in the output file has the format:
            <driver_id>\t<command line>

        Args:
            seed_placeholder: token used to stand for the input seed on the cmdline.
            out_path: optional path to the output file. If None, defaults to
                      <binary_path>/drivers/cmdlines.txt.

        Returns:
            List of (driver_id, cmdline_string).
        """
        driver_list_path = os.path.join(self.output_path, "driver_list.json")
        if not os.path.exists(driver_list_path):
            raise FileNotFoundError(f"driver_list.json not found at: {driver_list_path}")

        with open(driver_list_path, "r") as f:
            meta = json.load(f)

        drivers_meta = meta.get("drivers", [])
        if not isinstance(drivers_meta, list):
            raise ValueError(f"Malformed driver_list.json: 'drivers' is not a list")

        # Default output file
        if out_path is None:
            out_path = os.path.join(self.output_path, "cmdlines.txt")

        results: List[Tuple[int, str]] = []

        print(f"# Binary path: {self.binary_path}")
        print(f"# Executable:  {self.binary_name}")
        print(f"# Source:      {driver_list_path}")
        print(f"# Dump file:   {out_path}")
        print("# Format: <id>\\t<command line>\n")

        # Open once and write progressively
        with open(out_path, "w") as out_f:
            out_f.write(f"# binary_path: {self.binary_path}\n")
            out_f.write(f"# executable:  {self.binary_name}\n")
            out_f.write(f"# source:      {driver_list_path}\n")
            out_f.write("# format: <id>\\t<command line>\n\n")

            for entry in drivers_meta:
                # entry is like { "1": "1_p_auto" } (one key per dict)
                if not isinstance(entry, dict) or len(entry) != 1:
                    continue

                (id_str, drv_name), = entry.items()
                try:
                    drv_id = int(id_str)
                except ValueError:
                    # If keys are ints and drv_name is the name, you can adapt here;
                    # for now we skip malformed entries.
                    continue

                drv_dir = os.path.join(self.output_path, drv_name)
                drv_json_path = os.path.join(drv_dir, f"{drv_name}.json")

                if not os.path.exists(drv_json_path):
                    # silently skip missing drivers
                    continue

                with open(drv_json_path, "r") as f:
                    drv_obj = json.load(f)

                exe_name = drv_obj.get("driver", self.binary_name)
                args = drv_obj.get("args", [])
                output = drv_obj.get("output", "")

                binary_full = os.path.join(self.binary_path, exe_name)

                # Rebuild argv with the placeholder
                argv = [binary_full]
                argv += self._flatten_args(args)
                argv.append(seed_placeholder)
                if output:
                    argv += str(output).split()

                cmdline = " ".join(argv)
                line = f"{drv_id}\t{cmdline}\n"
                out_f.write(line)
                print(line, end="")

                results.append((drv_id, cmdline))

        print(f"[+] Dumped {len(results)} driver cmdlines to {out_path}")
        return results
