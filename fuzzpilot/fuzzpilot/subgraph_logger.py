import json
import os

class SubgraphLogger:
    def __init__(self, path="subgraph_stats.json"):
        self.log_path = path
        
        if os.path.exists(self.log_path):
            os.remove(self.log_path)

    def log(self, entry):
        """Appends a subgraph evaluation record as a JSON object."""
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
