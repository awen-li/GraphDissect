import time
import os
import sys
import signal
import shutil
import random
import subprocess
import shlex
from .scheduler import Scheduler

class FuzzPilot:
    def __init__(self, fuzzer, disable_embed_drift=False, disable_fcov_drift=False):
        self.fuzzer        = fuzzer
        self.fuzzer_proc   = None
        self.active_driver = 0
        self.covered_func  = 0
        self.fuzzing_stats = 0
        # Store ablation study parameters
        self.disable_embed_drift = disable_embed_drift
        self.disable_fcov_drift = disable_fcov_drift

        self.init_session ()

    def init_session (self):
        self.session_id = str(os.getpid())
        self.session_path = f"/tmp/hfuzz_{self.session_id}"
        if os.path.exists(self.session_path):
            shutil.rmtree(self.session_path)
        os.makedirs(self.session_path, exist_ok=False)

    def init_fuzzDirectory (self):
        fuzz_dir = os.path.abspath(os.path.join(".", "fuzz"))
        if not os.path.exists (fuzz_dir):
            os.makedirs(fuzz_dir, exist_ok=True)

        fuzz_in = os.path.abspath(os.path.join(fuzz_dir, "in"))
        if not os.path.exists (fuzz_in):
            os.makedirs(fuzz_in, exist_ok=True)

        fuzz_out = os.path.abspath(os.path.join(fuzz_dir, "out"))
        if not os.path.exists (fuzz_out):
            os.makedirs(fuzz_out, exist_ok=True)

        return fuzz_in, fuzz_out
    
    def process_exists(self, name="honggfuzz") -> bool:
        return subprocess.run(
            ["pgrep", "-f", name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0

    def start_fuzzer(self, benchmark, driverId=0):
        # change the directory to the bench
        absPath = os.path.abspath(benchmark)
        os.chdir(absPath)

        # init scheduler
        self.schduler = Scheduler(self.session_id, self.session_path, self.disable_embed_drift, self.disable_fcov_drift)

        if not self.schduler.init(absPath):
            sys.exit(0)

        if driverId == 0:
            self.active_driver = self.schduler.select_driver(None)
        else:
            self.active_driver = driverId
        self.schduler.set_active_driver(self.active_driver, init=True)

        # init fuzzing directory: in/out
        in_dir, out_dir = self.init_fuzzDirectory ()

        cmd = [
            self.fuzzer,
            "-n", "1",
            "-X", self.session_path,
            "-b", absPath,
            "-i", in_dir,
            "-o", out_dir,
            "--timeout", "10",
            "--rlimit_rss", "2048",
            "-F", "1048576",
            "--", "fuzzPilot",
            "___FILE___"
        ]

        # Export the exact honggfuzz command and working dir for external debugging
        try:
            cmd_str = " ".join(shlex.quote(x) for x in cmd)
            with open(os.path.join(self.session_path, "hfuzz_cmd.txt"), "w") as f:
                f.write(cmd_str + "\n")
            with open(os.path.join(self.session_path, "cwd.txt"), "w") as f:
                f.write(absPath + "\n")
            print(f"[FuzzPilot][debug] wrote honggfuzz command to {os.path.join(self.session_path, 'hfuzz_cmd.txt')}")
            print(f"[FuzzPilot][debug] working dir: {absPath}")
        except Exception as e:
            print(f"[FuzzPilot][debug] failed to export command: {e}")

        # Optional debug gate: pause here if FP_DEBUG defined until CONTINUE file appears
        if os.environ.get("FP_DEBUG") != None:
            while True:
                if self.process_exists ():
                    break
                print(f"[FP_DEBUG]waiting for honggfuzz setup....")
                time.sleep(0.5)
            print(f"[FP_DEBUG]honggfuzz has been setup....")
            return
        else:
            # Start the fuzzer in its own process group
            self.fuzzer_proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
            print(f"[FuzzPilot] [session - {self.session_id}]fuzzer started for fuzzing on {benchmark}")
            return

    def stop_fuzzer(self):
        if self.fuzzer_proc:
            self.fuzzer_proc.send_signal(signal.SIGINT)
            self.fuzzer_proc.wait()
            print("[FuzzPilot] fuzzer stopped.")
        self.schduler.deinit()
        shutil.rmtree(self.session_path)

    def check_fcov(self, driver_time_budget):
        check_interval = driver_time_budget/5

        time_budget = 0
        check_num   = 0
        while time_budget < driver_time_budget:
            time.sleep(check_interval)

            fuzzing_stats = self.schduler.get_fuzzing_stats()
            if self.fuzzing_stats != fuzzing_stats:
                print (f"[run_schedule][driver-{self.active_driver}][{check_num*check_interval}]"
                       f"edge-cov: {self.fuzzing_stats} -> {fuzzing_stats}\n")
                time_budget = 0
                self.fuzzing_stats = fuzzing_stats
            else:
                time_budget += check_interval
            check_num += 1

            if self.total_time + check_num*check_interval >= self.max_time_budget:
                break

        covered_funcs = self.schduler.get_covered_nodes()
        time_cost = check_num*check_interval
        print (f"[run_schedule][driver-{self.active_driver}][{time_cost}][{len(covered_funcs)}]coved_funcs -> {covered_funcs}\n")
        return time_cost
    
    def fuzz_by_average(self, max_time_budget):
        driver_list = self.schduler.get_all_drivers()
        if driver_list == None or len(driver_list) == 0:
            print ("No drivers are loaded!")
            self.stop_fuzzer()
            return 0
        
        switch_interval = max_time_budget/len(driver_list) 
        if switch_interval < 1:
            switch_interval = 1
            max_time_budget = len(driver_list)
        print(f"@fuzz_by_average -> drivers: {driver_list}, driver_num:{len(driver_list)}, switch_interval:{switch_interval}")

        total_time    = 0
        driver_index  = 0
        while total_time < max_time_budget:
            time.sleep(switch_interval)
            total_time += switch_interval

            # update active driver
            driver_index += 1

            if driver_index >= len(driver_list):
                driver_index = 0
            
            self.active_driver = driver_list[driver_index]
            self.schduler.set_active_driver(self.active_driver)
        return total_time

    def fuzz_by_random(self, driver_time_budget):
        total_time = 0
        driver_list = self.schduler.get_all_drivers()
        if driver_list == None or len(driver_list) == 0:
            print("No drivers are loaded!")
            self.stop_fuzzer()
            return 0

        print(f"@fuzz_by_random -> drivers: {driver_list}, driver_num:{len(driver_list)}")

        while self.total_time < self.max_time_budget:
            shuffuled_drivers = driver_list[:]
            random.shuffle(shuffuled_drivers)
            
            for driver_id in shuffuled_drivers:
                if self.total_time >= self.max_time_budget:
                    break
                print(f"@fuzz_by_random -> Fuzzing driver {driver_id} ...")
                self.active_driver = driver_id
                self.schduler.set_active_driver(driver_id)

                time_cost = self.check_fcov(driver_time_budget)
                total_time += time_cost
                self.total_time += time_cost

        return total_time

    def fuzz_by_static(self, driver_time_budget):
        total_time = 0
        driver_list = self.schduler.get_all_drivers()
        if driver_list == None or len(driver_list) == 0:
            print("No drivers are loaded!")
            self.stop_fuzzer()
            return 0

        print(f"@fuzz_by_static -> drivers: {driver_list}, driver_num:{len(driver_list)}")

        while self.total_time < self.max_time_budget:
            for driver_id in driver_list:
                if self.total_time >= self.max_time_budget:
                    break
                print(f"@fuzz_by_static -> Fuzzing driver {driver_id} ...")
                self.active_driver = driver_id
                self.schduler.set_active_driver(driver_id)

                time_cost = self.check_fcov(driver_time_budget)
                total_time += time_cost
                self.total_time += time_cost

        return total_time

    def pilot_fuzzing(self, pilot_budget):
        return self.fuzz_by_average(pilot_budget)

    def fallback_fuzzing(self, driver_time_budget, topK=32):
        """
        Fallback fuzzing mode:
        - Use statically prioritized drivers (ordered by static priority).
        - Each driver is fuzzed for `driver_time_budget` seconds.
        - Returns total time spent in fallback mode.
        
        Args:
            driver_time_budget (int): Time (in seconds) allocated per driver.
            topK (int): Number of top static-priority drivers to include.
            
        Returns:
            int: Total time spent in fallback fuzzing.
        """
        total_time = 0
        print("[fallback_fuzzing] Starting fallback fuzzing...")

        driver_list = self.schduler.get_all_drivers()
        if not driver_list:
            print("[fallback_fuzzing] No drivers are loaded!")
            self.stop_fuzzer()
            return 0

        fallback_drivers = driver_list[:topK]
        print(f"[fallback_fuzzing] Selected top-{len(fallback_drivers)} drivers for fallback fuzzing.")

        index = 1
        for driver_id in fallback_drivers:
            print(f"[fallback_fuzzing][{index}/{topK}] Fuzzing driver {driver_id} ...")
            self.active_driver = driver_id
            self.schduler.set_active_driver(driver_id)

            time_cost = self.check_fcov(driver_time_budget)
            total_time += time_cost

            index += 1

        print(f"[fallback_fuzzing] Fallback mode complete. Total time spent: {total_time}s")
        return total_time

    def is_single_driver_mode(self):
        all_drivrs = self.schduler.get_all_drivers()
        return all_drivrs is not None and len(all_drivrs) == 1
    
    def run_single_driver(self, max_time_budget=24 * 3600):
        self.total_time = 0
        self.max_time_budget = max_time_budget

        while self.total_time < self.max_time_budget:
            print(f"[run_single_driver] Fuzzing driver {self.active_driver} ...")
            time.sleep(60)
            self.total_time += 60

            covered_funcs = self.schduler.get_covered_nodes()
            print(f"[run_schedule-pilot][{len(covered_funcs)}] covered_funcs -> {covered_funcs}\n")

        # Final coverage report
        covered_funcs = self.schduler.get_covered_nodes()
        print(f"[run_single_driver][{len(covered_funcs)}] covered_funcs -> {covered_funcs}\n")
        self.stop_fuzzer()

    def run_schedule(self, driver_time_budget, max_time_budget=24 * 3600):
        """
        State-machine-based scheduling strategy:
        - Pilot mode: average scheduling to train the initial model.
        - Dynamic mode: reinforcement learning-based driver selection.
        Fallback to pilot mode if no driver contributes (plateau detection).
        """
        self.total_time = 0
        self.max_time_budget = max_time_budget

        state = 'pilot'
        pilot_fuzz_budget = self.max_time_budget * 0.05

        while self.total_time < self.max_time_budget:
            if state == 'pilot':
                print("[State] Entering Pilot Fuzzing Mode (Average Scheduling)")
                time_cost = self.pilot_fuzzing(pilot_fuzz_budget)
                if time_cost  == 0:
                    print("[Error] Pilot fuzzing failed.")
                    return

                self.total_time += time_cost
                state = 'dynamic'

                covered_funcs = self.schduler.get_covered_nodes()
                print(f"[run_schedule-pilot][{len(covered_funcs)}] covered_funcs -> {covered_funcs}\n")

            elif state == 'dynamic':
                print("[State] Entering Dynamic Scheduling Mode")
                drv_runtime_stats = self.schduler.get_driver_runtimes()

                # Plateau detection: no driver has contributed new edges
                edge_deltas = [v.get("delta_edges", 0) for v in drv_runtime_stats.values()]
                if all(delta == 0 for delta in edge_deltas):
                    print("[State] Detected plateau in edge coverage. Re-entering Pilot Fuzzing Mode.")
                    state = 'fallback'
                    continue

                # Select and run the next active driver
                self.active_driver = self.schduler.select_driver(drv_runtime_stats)
                self.schduler.set_active_driver(self.active_driver)

                driver_time_cost = self.check_fcov(driver_time_budget)
                self.total_time += driver_time_cost

            elif state == 'fallback':
                print("[State] Entering Fallback Scheduling Mode")
                self.total_time += self.fallback_fuzzing(driver_time_budget)
                state = 'dynamic'

        # Final coverage report
        covered_funcs = self.schduler.get_covered_nodes()
        print(f"[run_schedule][{len(covered_funcs)}] covered_funcs -> {covered_funcs}\n")
        self.stop_fuzzer()


    def run_schedule_average(self, max_time=24*3600):
        self.max_time_budget = max_time

        if self.fuzz_by_average(max_time) == 0:
            return

        coved_funcs = self.schduler.get_covered_nodes()
        print (f"[run_schedule_average][{len(coved_funcs)}]coved_funcs -> {coved_funcs}\n")
        self.stop_fuzzer()

    def run_schedule_random(self, driver_time_budget, max_time_budget=24 * 3600):
        self.total_time = 0
        self.max_time_budget = max_time_budget

        if self.fuzz_by_random(driver_time_budget) == 0:
            return

        coved_funcs = self.schduler.get_covered_nodes()
        print (f"[run_schedule_random][{len(coved_funcs)}]coved_funcs -> {coved_funcs}\n")
        self.stop_fuzzer()

    def run_schedule_static(self, driver_time_budget, max_time_budget=24 * 3600):
        self.total_time = 0
        self.max_time_budget = max_time_budget

        if self.fuzz_by_static(driver_time_budget) == 0:
            return

        coved_funcs = self.schduler.get_covered_nodes()
        print (f"[run_schedule_static][{len(coved_funcs)}]coved_funcs -> {coved_funcs}\n")
        self.stop_fuzzer()
