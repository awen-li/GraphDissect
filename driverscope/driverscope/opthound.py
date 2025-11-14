import os
import json
from abc import ABC, abstractmethod
from typing import List
from driverscope.drivergen import DriverGenerator
from driverscope.option import Option

class OptHound(ABC):
    def __init__(self, benchmark_path, binary_path):
        self.binary_path    = os.path.abspath(binary_path)
        self.benchmark_path = os.path.abspath(benchmark_path)

    @abstractmethod
    def extract_options(self) -> List[Option]:
        return {
            "--html": "use the HTML parser",
            "--valid": "validate the document",
            # ...
        }

    def generate_driver_jsons(self, options: List[Option]):
        generator = DriverGenerator(self.binary_path, self.benchmark_path, options)
        return generator.generate()

    def run(self):
        options = self.extract_options()

        # Insert a default (no-option) entry
        default_option = Option(option="", arg=None, description="default mode", type_hint="default")
        options.insert(0, default_option)

        return self.generate_driver_jsons(options)
