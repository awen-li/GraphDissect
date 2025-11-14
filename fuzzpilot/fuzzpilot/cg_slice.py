import os
import dynsch

class CgSlice:
    def __init__(self, bench_path: str ='.', max_depth: int = 4096):
        self.bench_path = os.path.abspath(bench_path)
        self.max_depth  = max_depth

    def slice(self):
        dynsch.sliceMarkedGraph(self.max_depth)

    def stat(self, drv_ids):
        dynsch.getDriverStatistic(self.bench_path, drv_ids) 
