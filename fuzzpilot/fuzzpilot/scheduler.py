import torch
import time
import dynsch
from .contrastive_trainer import ContrastiveGraphTrainer
from .drift_scheduler import DriftBasedScheduler
from .driver_graph import DriverGraph
from .perf_logger import PerfLogger

class Scheduler:
    def __init__(self, session_id, session_path, disable_embed_drift=False, disable_fcov_drift=False):
        self.graph_loader = DriverGraph()
        self.driver_ids   = None
        self.trained_num  = 0
        self.bench_path   = ""
        self.session_path = session_path
        self.selected_drivers = {}
        # Store ablation study parameters
        self.disable_embed_drift = disable_embed_drift
        self.disable_fcov_drift = disable_fcov_drift

        # init session
        dynsch.initSession(int(session_id), session_path)
        
        # Initialize training + scheduling
        self.trainer = ContrastiveGraphTrainer()
        self.scheduler = DriftBasedScheduler(self.trainer, self.disable_embed_drift, self.disable_fcov_drift)

        self.perf = PerfLogger()

    def _read_fuzzing_stats(self, stat_path="driver_runtimes/overview.stat", verbose=False):
        """
        Parses a driver_runtimes/overview.stat file with format:
        edges:8600, crashes:0, time:3581

        Args:
            target_key (str): The key to retrieve (e.g., "edges", "crashes", "time").
            stat_path (str): Path to the stat file.
            verbose (bool): If True, print the entire parsed stats.

        Returns:
            int: Value associated with target_key, or 0 if not found.
        """
        fstats = {}
        try:
            with open(stat_path, 'r') as f:
                line = f.readline().strip()
                entries = line.split(',')
                for entry in entries:
                    if ':' in entry:
                        k, v = entry.strip().split(':', 1)
                        fstats[k.strip()] = int(v.strip())
        except Exception as e:
            print(f"[!] Failed to parse {stat_path}: {e}")
            return 0

        if verbose:
            print(f"[+] Parsed stats: {fstats}")

        return fstats
    

    def get_fuzzing_stats(self):
        fuzz_stats = self._read_fuzzing_stats()
        keys = ["edges", "crashes", "pc", "cmp"]
        return [fuzz_stats.get(key, 0) for key in keys]


    def get_driver_runtimes(self) -> dict:
        driver_stats = {}
        for driver_id in self.driver_ids:
            stat = dynsch.getDriverRTStat(driver_id)

            if stat is None or not isinstance(stat, dict):
                raise RuntimeError(f"[collect_driver_runtimes] Failed to get runtime stat for driver {driver_id}")
            
            driver_stats[driver_id] = stat

        # After collecting all stats, print only non-zero items
        non_zero_stat = {}
        for driver_id, stat in driver_stats.items():
            non_zero_item = {k: v for k, v in stat.items() if isinstance(v, (int, float)) and v != 0}
            if non_zero_item:
                non_zero_stat[driver_id] = non_zero_item
        print(f"@get_driver_runtimes: non_zero_stat =\n\t {non_zero_stat}")

        return driver_stats

    def get_all_drivers(self):
        return self.driver_ids
    
    def get_covered_nodes(self):
        return dynsch.getCoveredFuncs()
    
    def set_active_driver(self, driver_id, init=False):
        if init == False:
            dynsch.setActiveDriver (driver_id)
        else:
            dynsch.setInitDriver (driver_id)

    def save_selects(self, driver_id):
        if driver_id not in self.selected_drivers:
            self.selected_drivers[driver_id] = 1
        else:
            self.selected_drivers[driver_id] += 1

    def init(self, bench_path):
        # init scheduler for the benchmark
        if not dynsch.initScheduler (bench_path):
            print(f"[Scheduler] initScheduler failed @{bench_path}")
            return False
        print(f"[Scheduler] initScheduler success @{bench_path}")

        self.driver_ids = dynsch.getAllDrivers()
        if len(self.driver_ids) == 0:
            print(f"[Scheduler] get drivers failed @{bench_path}")
            return False
        
        self.wgraph_size = dynsch.getWGraphSize()
        self.bench_path  = bench_path

        print(f"[Scheduler] get drivers success, total derivers: {len(self.driver_ids)}")
        return True

    def deinit(self):
        dynsch.deinitSession()
        # Sort the dict by execution count (value), descending
        sorted_stats = dict(
            sorted(self.selected_drivers.items(), key=lambda x: x[1], reverse=True)
        )
        print(f"[{len(sorted_stats)}] {sorted_stats}")


    def get_driver_subgraph(self, driver_id):
        return self.graph_loader.get_driver_subgraph(driver_id)

    def perform_train(self):
        self.graph_loader.syn_graphs()   # update dynamic subgraphs

        start = time.time()
        subgraphs = []
        for did in self.driver_ids:
            g = self.get_driver_subgraph(did)
            if g == None:
                continue
            subgraphs.append(g)
        if len(subgraphs) == 0:
            return

        self.perf.start()

        self.trainer.train_one_epoch(subgraphs)

        stats = self.perf.stop()
        self.perf.log(f"{self.trained_num}", stats)

        self.trained_num += 1
        print(f"@[Scheduler][{self.trained_num}]perform_train success, #subgraphs = {len(subgraphs)}/{len(self.driver_ids)} time-cost = {time.time()-start}")

    def select_driver(self, drv_runtime_stats):
        selected_driver = 0
        if self.trained_num < 2:
            selected_driver = dynsch.getPriorDriver()  # static priority before training
        else:
            top_drivers = self.scheduler.select_top_driver(self.wgraph_size, 
                                                           self.driver_ids, 
                                                           self.get_driver_subgraph, 
                                                           drv_runtime_stats,
                                                           k=3)
            print("[Scheduler]Top drivers by embedding drift:", top_drivers)

            top_driver_id, top_drift = top_drivers[0]
            if top_drift == 0 or top_drift == float('inf'):
                selected_driver = dynsch.getPriorDriver()  # fallback to static scheduling
            else:
                selected_driver = top_driver_id
        
        # train for next computation
        self.perform_train() 

        self.save_selects(selected_driver)
        return selected_driver
