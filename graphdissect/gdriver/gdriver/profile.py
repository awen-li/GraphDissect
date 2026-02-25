import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


# =========================
# IO SPECIFICATIONS
# =========================

@dataclass
class InputSpec:
    kind: str = "positional"          # "positional" | "flagged"
    flag: Optional[str] = None        # e.g., "-i" when kind == "flagged"


@dataclass
class OutputSpec:
    kind: str = "positional"          # "positional" | "flagged"
    flag: Optional[str] = None        # e.g., "-o" when kind == "flagged"


@dataclass
class IOSpec:
    input: InputSpec = field(default_factory=InputSpec)
    output: OutputSpec = field(default_factory=OutputSpec)


# =========================
# BINARY PROFILE
# =========================

class BinProfile:
    def __init__(
        self,
        name: str,
        binary: str,
        domain: str,
        seed_dir: str,
        max_combination: int = 2,
        base_args: Optional[List[str]] = None,
        io: Optional[IOSpec] = None,
    ):
        self.name = name
        self.binary = binary
        self.domain = domain
        self.seed_dir = seed_dir
        self.max_combination = max_combination
        self.base_args = base_args if base_args is not None else []
        self.io = io

    @classmethod
    def from_dict(cls, d: dict):
        """
        d is the dict under 'profile:' in the YAML, e.g.:

        profile:
          name: "ffmpeg"
          binary: "ffmpeg"
          domain: "media"
          seed_dir: "seeds"
          max_combination: 2
          base_args: ["-nostdin", "-y"]
          io:
            input:
              kind: "flagged"
              flag: "-i"
            output:
              kind: "positional"
              flag: ""
        """
        # --- IO parsing ---
        io_data = d.get("io", {}) or {}
        input_data = io_data.get("input", {}) or {}
        output_data = io_data.get("output", {}) or {}

        input_spec = InputSpec(
            kind=input_data.get("kind", "positional"),
            flag=input_data.get("flag"),
        )

        output_spec = OutputSpec(
            kind=output_data.get("kind", "positional"),
            flag=output_data.get("flag"),
        )

        io_spec = IOSpec(input=input_spec, output=output_spec)

        # --- core fields ---
        return cls(
            name=d["name"],
            binary=d.get("binary", d["name"]),
            domain=d.get("domain", "unknown"),
            seed_dir=d.get("seed_dir", "seeds"),
            max_combination=d.get("max_combination", 2),
            base_args=d.get("base_args", []),
            io=io_spec,
        )

    def __repr__(self):
        return (
            f"BinProfile(name={self.name!r}, binary={self.binary!r}, "
            f"domain={self.domain!r}, seed_dir={self.seed_dir!r}, "
            f"max_combination={self.max_combination}, "
            f"io={self.io})"
        )

