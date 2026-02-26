from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
import sgmarker


@dataclass
class Driver:
    id: int = -1
    name: str = ""
    driver: str = ""          # executable name, e.g., "xmllint"
    args: list[str] = None    # arguments list
    seed_dir: str = ""
    output: str = ""
    priority: float = 1.0
    description: str = ""

    @classmethod
    def from_dict(cls, spec: dict[str, Any]) -> "Driver":
        # tolerate missing fields
        return cls(
            id=int(spec.get("id", -1)),
            name=str(spec.get("name", "")),
            driver=str(spec.get("driver", "")),
            args=list(spec.get("args", [])) if spec.get("args") is not None else [],
            seed_dir=str(spec.get("seed_dir", "")),
            output=str(spec.get("output", "")),
            priority=float(spec.get("priority", 1.0)),
            description=str(spec.get("description", "")),
        )


class DrvGraph:
    def __init__(self, benchPath: str | Path, binaryName: str):
        self.benchPath = Path(benchPath)
        self.binaryName = binaryName

        # driver_id (int) -> Driver
        self.drvList: Dict[int, Driver] = {}

        self.binaryDir      = self.benchPath / self.binaryName
        self.driversDir     = self.binaryDir / "drivers"
        self.driverListJson = self.driversDir / "driver_list.json"

        self._load_drivers()
        sgmarker.init(str(self.binaryDir))

    def _load_driver_spec(self, spec_path: Path) -> dict:
        return json.loads(spec_path.read_text())

    def _load_drivers(self) -> None:
        self.drvList.clear()

        if not self.driverListJson.is_file():
            msg = f"missing driver_list.json: {self.driverListJson}"
            print(f"Warning: {msg}")
            return

        meta = json.loads(self.driverListJson.read_text())
        entries = meta.get("drivers", [])
        if not isinstance(entries, list):
            raise ValueError(f"Unexpected format: 'drivers' is {type(entries)}")

        for one in entries:
            # each element is like { "1": "1_default" }
            if not isinstance(one, dict) or len(one) != 1:
                if strict:
                    raise ValueError(f"Bad driver_list entry: {one}")
                continue

            (drvIdRaw, drvNameRaw), = one.items()
            drvId = int(drvIdRaw)
            drvName = str(drvNameRaw)

            drvDir = self.driversDir / drvName
            specPath = drvDir / f"{drvName}.json"

            if not specPath.is_file():
                msg = f"missing driver spec: {specPath}"
                if strict:
                    raise FileNotFoundError(msg)
                print(f"Warning: {msg}")
                continue

            spec = self._load_driver_spec(specPath)
            drv = Driver.from_dict(spec)
            self.drvList[drv.id] = drv

    def get_driver_graph(self, drvId: int):
        return sgmarker.getDriverGraph(drvId)

    def get_graph_coverage(self):
        # (nodeCov, edgeCov)
        return sgmarker.getGraphCov()
