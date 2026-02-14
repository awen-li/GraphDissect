# gdist/registry.py
from __future__ import annotations

from typing import Dict, List, Sequence, Type

from gdist.analyzers.analyzer import Analyzer

_REG: Dict[str, Analyzer] = {}


def register(cls: Type[Analyzer]) -> Type[Analyzer]:
    inst = cls()
    if inst.key in _REG:
        raise ValueError(f"Duplicate analyzer key: {inst.key}")
    _REG[inst.key] = inst
    return cls


def all_analyzers() -> List[Analyzer]:
    return [ _REG[k] for k in sorted(_REG.keys()) ]


def select(keys: Sequence[str]) -> List[Analyzer]:
    out: List[Analyzer] = []
    for k in keys:
        if k not in _REG:
            raise KeyError(f"Unknown analyzer '{k}'. Available: {sorted(_REG.keys())}")
        out.append(_REG[k])
    return out
