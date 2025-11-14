import os
import re
import json
import copy
import shutil
import random
import string
import subprocess
from typing import List, Any, Optional
from itertools import combinations
from driverscope.llmagent import OpenAIAgent, DPAgent
from driverscope.project import Project
from driverscope.option import Option

class Driver:
    def __init__(self, id, name, driver, args, seed_dir="seeds", output="", priority=1.0, description=""):
        self.id     = id
        self.name   = name
        self.driver = driver
        self.args   = args
        self.seed_dir = seed_dir
        self.output   = output
        self.priority = priority
        self.description = description
        self.primary = True

    def get_seeds(self, seed_dir, prefix="seed"):
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
        
        files = [
            f for f in os.listdir(seed_dir) if f.startswith(prefix)
        ]
        # Sort by numeric suffix (e.g., seed1, seed2, ..., seed10)
        files.sort(key=lambda x: int(''.join(filter(str.isdigit, x))))
        return [os.path.join(seed_dir, f) for f in files]

    def calibrate(self, binary: str, seed_list: List[str]) -> bool:
        """
        Test if this driver configuration can run standalone (without crashing or critical failure).

        Args:
            binary: Path to the target binary.
            seed_list: List of input seed file paths.

        Returns:
            True if the driver appears valid (some seeds worked), False otherwise.
        """
        failed = 0

        for seed in seed_list:
            # Construct the command line: binary + static args + input seed + output path
            cmd = (
                [binary] +
                [f"{arg}" for arg in self.args if arg not in ("", None)] +
                [seed] +
                ([self.output] if self.output not in ("", None) else [])
            )
            
            try:
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                stderr_output = result.stderr.decode(errors="ignore").lower()

                print(f"calibrate --> {cmd}")

                # Use common keywords to heuristically detect failures
                if any(kw in stderr_output for kw in ["missing", "required", "invalid", "usage", "failed"]):
                    #print(f"\t{' '.join(cmd)} --> error occurs: {stderr_output}")
                    failed += 1
                    os.remove(seed)

            except Exception as e:
                print(f"Exception while testing {cmd}: {e}")
                failed += 1
                os.remove(seed)

        # If all seeds failed, mark driver as not primary
        if failed >= len(seed_list):
            self.primary = False

        print(f"{self.driver} --> self.primary = {self.primary}, failed = {failed}")
        return self.primary


    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "driver": self.driver,
            "args": self.args,
            "seed_dir": self.seed_dir,
            "output": self.output,
            "priority": self.priority,
            "description": self.description
        }


class DriverGenerator:
    def __init__(self, binary_path: str, benchmark_path: str, option_list: List[Option]):
        self.binary_path    = binary_path
        self.benchmark_path = benchmark_path
        self.option_list    = option_list
        self.output_path    = os.path.join(benchmark_path, "drivers")
        self.project        = Project(os.path.join(benchmark_path, "project.yaml"))
        self.max_seeds_num  = 128
        #self.llm = OpenAIAgent()
        self.llm  = DPAgent()

    def get_driver_root(self, driver):
        return str(driver.id) + "_" + driver.name
    
    def _remove_driver_id(self, driver_name: str) -> str:
        return re.sub(r'^\d+_', "", driver_name) 

    def create_new_driver(self, base: Driver, args: List[str], driver_id: int = -1, suffix: str = "") -> Driver:
        """
        Create a new Driver by copying the base driver and replacing the args.
        Also copies the seed files to a new seed directory for the new driver.

        Args:
            base: The original Driver instance to copy from.
            args: A new list of arguments for the new driver.
            suffix: A suffix to append to the driver name.

        Returns:
            A new Driver instance with a new seed directory.
        """
        new_name = self._remove_driver_id(base.name) + "_" + suffix
        new_driver = Driver(
            id=driver_id,
            name=new_name,
            driver=base.driver,
            args=args,
            seed_dir="seeds",
            output=base.output,
            priority=base.priority,
            description=base.description
        )

        # Copy seed files
        new_seed_dir = os.path.join(self.output_path, self.get_driver_root(new_driver), "seeds")
        if os.path.exists(base.seed_dir):
            os.makedirs(new_seed_dir, exist_ok=True)
            seed_no = 1
            for fname in os.listdir(base.seed_dir):
                src = os.path.join(base.seed_dir, fname)
                dst = os.path.join(new_seed_dir, f"seed{seed_no}")
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    seed_no += 1

        return new_driver

    def combine_main(self, succeed_drivers: List[Driver], failed_drivers: List[Driver], start_id: int) -> List[Driver]:
        """
        Combine full argument lists from failed drivers with successful drivers
        to generate new hybrid drivers.

        Args:
            succeed_drivers: List of drivers that passed calibration.
            failed_drivers: List of drivers that failed calibration.

        Returns:
            A list of new Driver instances created by appending failed args to successful ones.
        """
        new_drivers: List[Driver] = []
        print(f"@combine_main: succeed_drivers -> {len(succeed_drivers)}, failed_drivers -> {len(failed_drivers)}")
        for failed in failed_drivers:
            for success in succeed_drivers:
                if success.args[0] == failed.args[0] or failed.name == "default":
                    continue

                new_args: List[str] = success.args + failed.args

                new_driver: Driver = self.create_new_driver(
                    base=success,
                    args=new_args,
                    driver_id=start_id,
                    suffix=failed.name
                )

                print(f"[+] Generated recombined driver: {new_driver.name} -> {new_args}")

                # Calibrate new driver
                seed_path = os.path.join(self.output_path, self.get_driver_root(new_driver), "seeds")
                seed_list = new_driver.get_seeds(seed_path)
                #print(f"seed_list: {new_driver.seed_dir} --> {seed_list}")
                if new_driver.calibrate(self.binary_path, seed_list):
                    print(f"[✓] Driver {new_driver.name} passed calibration")
                    new_drivers.append(new_driver)
                    start_id += 1

                    self.write_driver(new_driver)
                else:
                    print(f"[✗] Driver {new_driver.name} failed calibration")
                    self.remover_driver(new_driver)

        return new_drivers
        

    def get_driver_output(self) -> Optional[str]:
        """
        Determines the output path based on the command-line template.

        Returns:
            - "." if the output is a directory placeholder ({output:dir})
            - "/dev/null" if the output is a file placeholder ({output:file})
            - None if no output placeholder is found
        """
        cmdline: str = self.project.cmdline

        # Match placeholders like {output:dir} or {output:file}
        match = re.search(r'\{output:(dir|file)\}', cmdline)
        if not match:
            return ""  # No output placeholder found
        print(f"get_driver_output -> {cmdline} --> {match}")
        out_type: str = match.group(1)
        if out_type == "dir":
            return "."  # Default to current directory
        elif out_type == "file":
            return "/dev/null"  # Discard output by default

        return ""  # Fallback in case of unexpected match
    

    def gen_seed(self, driver) -> List[str]:
        """
        Generate or copy seeds for a given driver.

        Steps:
        - If `seeds/` exists under the benchmark, copy its contents to the driver's seed path.
        - Otherwise, use LLM to generate seeds if too few are found.
        
        Returns:
            A list of paths to seed files.
        """
        # Path to save seeds specific to this driver
        seed_path = os.path.join(self.output_path, self.get_driver_root(driver), "seeds")
        os.makedirs(seed_path, exist_ok=True)

        # Initial seeds that come with the benchmark
        initial_seeds_dir = os.path.join(self.benchmark_path, "seeds")
        #print(f"@gen_seed --> {initial_seeds_dir}")

        if os.path.exists(initial_seeds_dir):
            # Copy all initial seeds into the driver's seed directory
            seed_no = 100
            for f in os.listdir(initial_seeds_dir):
                src = os.path.join(initial_seeds_dir, f)
                dst = os.path.join(seed_path, f"seed{seed_no}")
                seed_no += 1

                if os.path.isfile(src) and not os.path.exists(dst):
                    try:
                        os.symlink(src, dst)
                        print(f"@gen_seed link {src} -> {dst} succeeded")
                    except FileExistsError:
                        print(f"[!] Link already exists: {dst}")
                    except OSError as e:
                        print(f"[!] Failed to link {src} -> {dst}: {e}")

        # Try to get existing seeds (after copying or checking)
        all_seeds = driver.get_seeds(seed_path)
        if len(all_seeds) > self.max_seeds_num:
            seed_list = all_seeds[:self.max_seeds_num]
        else:
            seed_list = all_seeds

        # If too few seeds, call the LLM to generate more
        if len(seed_list) <= 5:
            self.llm.generate_seeds(self.project, driver, seed_path)
            seed_list = driver.get_seeds(seed_path)

        return seed_list
    
    def is_driver_exist(self):
        driver_list_path = os.path.join(self.output_path, "driver_list.json")
        if os.path.exists(driver_list_path):
            return True
        else:
            return False
    
    def remover_driver(self, driver):
        driver_path = os.path.join(self.output_path, self.get_driver_root(driver))
        if os.path.exists(driver_path):
            try:
                shutil.rmtree(driver_path)
            except:
                pass

    def get_opt_values(self, driver, opt, num=3) -> List[Any]:
        values = self.llm.get_opt_values(driver.driver, opt.option, opt.arg, driver.description, num)
        print(f"@@get_opt_values: {driver.driver} {driver.args} --> {values}")
        return values
    
    def gen_driver_list(self, drivers):
        driver_list_path = os.path.join(self.output_path, "driver_list.json")

        # Convert drivers to a list of {id: name} dictionaries
        driver_dict_list = [{d.id: d.name} for d in drivers]

        driver_list_obj = {
            "number": len(driver_dict_list),
            "drivers": driver_dict_list
        }

        with open(driver_list_path, "w") as f:
            json.dump(driver_list_obj, f, indent=4)
        print(f"[+] Generated {len(driver_dict_list)} drivers at: {driver_list_path}")

    def localize_path(self, arg: str, work_dir: str = ".") -> str:
        """
        If the argument is a path like /usr/local/etc/filename, convert it to ./filename
        and create a random file with that name.

        Returns the updated (localized) path.
        """
        # Only convert absolute-looking paths (could customize further)
        if not arg.startswith("/"):
            if not arg.startswith("/"):
                if " " in arg:
                    arg = "\"" + arg.replace('"', '\\"') + "\""
            return arg

        filename = os.path.basename(arg)
        local_path = os.path.join(work_dir, filename)

        if not os.path.isdir(local_path):
            # Create a random file with placeholder content
            with open(local_path, "w") as f:
                f.write("random_config_" + ''.join(random.choices(string.ascii_letters, k=10)) + "\n")

        return local_path
    
    def write_driver(self, driver):
        driver_name = self.get_driver_root(driver)
        driver.name = driver_name
        driver_path = os.path.join(self.output_path, driver_name)
        os.makedirs(driver_path, exist_ok=True)
        with open(os.path.join(driver_path, f"{driver_name}.json"), "w") as f:
            json.dump(driver.to_json(), f, indent=4)
        return

    def generate(self):
        if self.is_driver_exist():
            return True
        
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")
        os.makedirs(self.output_path, exist_ok=True)

        drivers = []
        failed_drivers = []
        value_num  = 3
        com_failed = self.option_list[-1].comb_failed

        driver_id = 1
        for option_obj in self.option_list:
            name = option_obj.option.lstrip('-').replace('-', '_').replace(' ', '_')
            if option_obj.type == "default":
                name = "default"

            print(f"\n\n@generate driver [{driver_id}] for option: {option_obj.option}")
            driver = Driver(
                id=driver_id,
                name=name,
                driver=os.path.basename(self.binary_path),
                args=[option_obj.option],
                seed_dir="seeds",
                output=self.get_driver_output(),
                priority=1.0,
                description=option_obj.description
            )
            
            opt_values = [""] # empty by default
            if option_obj.arg != None:
                if option_obj.arg != '/dev/null': 
                    opt_values = self.get_opt_values(driver, option_obj, value_num)
                else:
                    opt_values = ["/dev/null"]

            sub_driver_no = 1
            for value in opt_values:
                new_driver = copy.deepcopy(driver)
                new_driver.id = driver_id
                if value != "":
                    new_driver.name += "_" + str(sub_driver_no)
                    opt_value = self.localize_path(value, self.benchmark_path)
                    new_driver.args.append(opt_value[:256])
                
                if option_obj.action != "":
                    new_driver.args.append(option_obj.action)
                    new_driver.name += "_" + option_obj.action

                sub_driver_no += 1

                # generate initial seeds for the driver
                seed_list = self.gen_seed(new_driver)

                # do calibration
                success = new_driver.calibrate(self.binary_path, seed_list)
                if success == False:
                    self.remover_driver(new_driver)
                    failed_drivers.append(new_driver)
                    continue

                drivers.append(new_driver)
                driver_id += 1

                # Write individual driver JSON file
                self.write_driver(new_driver)
        
        # Try to find valid combinations
        print(f"@generate: com_failed -> {com_failed}")
        if com_failed == True:
            drivers += self.combine_main(drivers, failed_drivers, driver_id)

        # Write driver_list.json
        self.gen_driver_list(drivers)
        return True


