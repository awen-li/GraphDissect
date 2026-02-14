from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any


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

        self.exe_dir = self.benchPath / self.binaryName
        self.drivers_dir = self.exe_dir / "drivers"
        self.driver_list_json = self.drivers_dir / "driver_list.json"

    def _load_driver_spec(self, spec_path: Path) -> dict:
        return json.loads(spec_path.read_text())

    def _load(self, strict: bool = True) -> None:
        self.drvList.clear()

        if not self.driver_list_json.is_file():
            msg = f"missing driver_list.json: {self.driver_list_json}"
            if strict:
                raise FileNotFoundError(msg)
            print(f"Warning: {msg}")
            return

        meta = json.loads(self.driver_list_json.read_text())
        entries = meta.get("drivers", [])
        if not isinstance(entries, list):
            raise ValueError(f"Unexpected format: 'drivers' is {type(entries)}")

        for one in entries:
            # each element is like { "1": "1_default" }
            if not isinstance(one, dict) or len(one) != 1:
                if strict:
                    raise ValueError(f"Bad driver_list entry: {one}")
                continue

            (drv_id_raw, drv_name_raw), = one.items()
            drv_id = int(drv_id_raw)
            drv_name = str(drv_name_raw)

            drv_dir = self.drivers_dir / drv_name
            spec_path = drv_dir / f"{drv_name}.json"

            if not spec_path.is_file():
                msg = f"missing driver spec: {spec_path}"
                if strict:
                    raise FileNotFoundError(msg)
                print(f"Warning: {msg}")
                continue

            spec = self._load_driver_spec(spec_path)

            # optional strict sanity check
            if strict:
                if "id" in spec and int(spec["id"]) != drv_id:
                    raise ValueError(f"id mismatch: list={drv_id} spec={spec.get('id')} ({spec_path})")
                if "name" in spec and str(spec["name"]) != drv_name:
                    raise ValueError(f"name mismatch: list={drv_name} spec={spec.get('name')} ({spec_path})")

            drv = Driver.from_dict(spec)
            self.drvList[drv.id] = drv
