import time
import os
import psutil

class PerfLogger:
    def __init__(self, log_file="perf_log.log"):
        self.process = psutil.Process(os.getpid())
        self.log_file = log_file

        if os.path.exists(log_file):
            os.remove(log_file)

    def start(self):
        self.start_time = time.perf_counter()
        self.start_mem = self.process.memory_info().rss

    def stop(self):
        end_time = time.perf_counter()
        end_mem = self.process.memory_info().rss

        elapsed_time = end_time - self.start_time
        mem_diff = end_mem - self.start_mem
        mem_usage = end_mem / (1024 * 1024)  # in MB

        return {
            "time_sec": elapsed_time,
            "memory_used_mb": mem_usage,
            "memory_diff_mb": mem_diff / (1024 * 1024)
        }

    def log(self, label, stats):
        line = (f"[PerfLog] {label} | Time: {stats['time_sec']:.3f}s "
                f"| Mem Used: {stats['memory_used_mb']:.1f}MB "
                f"| Delta: {stats['memory_diff_mb']:.1f}MB")

        print(line)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
