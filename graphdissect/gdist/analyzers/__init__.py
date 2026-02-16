# gdist/analyzers/__init__.py
from __future__ import annotations
from typing import Dict, List, Sequence, Type
from .analyzer import Analyzer, AnalysisContext, AnalysisResult

# bring analyzers into registry
from .rq1_contribution import RQ1Contribution
from .rq2_modularity import RQ2Modularity
from .rq3_overlap import RQ3Overlap
#from .rq4 import RQ4Correlation
#from .rq5 import RQ5BlindSpots

__all__ = [
    "Analyzer", "AnalysisContext", "AnalysisResult",
    "RQ1Contribution", 
    "RQ2Modularity", 
    "RQ3Overlap", 
#    "RQ4Correlation", 
#    "RQ5BlindSpots",
]


# Register analyzer *classes* (not instances)
_REG: Dict[str, Type[Analyzer]] = {
    "rq1": RQ1Contribution,
    "rq2": RQ2Modularity,
    "rq3": RQ3Overlap,
    # ...
}

def all_analyzers() -> List[Analyzer]:
    return [ _REG[k] for k in sorted(_REG.keys()) ]


def select(keys: Sequence[str]) -> List[Analyzer]:
    out: List[Analyzer] = []
    for k in keys:
        if k not in _REG:
            raise KeyError(f"Unknown analyzer '{k}'. Available: {sorted(_REG.keys())}")
        out.append(_REG[k])
    return out
