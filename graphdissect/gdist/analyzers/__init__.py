# gdist/analyzers/__init__.py
from __future__ import annotations
from typing import Dict, List, Sequence, Type
from .analyzer import Analyzer, AnalysisContext, AnalysisResult

# bring analyzers into registry
from .rq1_contribution import RQ1Contribution
from .rq3_modularity import RQ3Modularity
from .rq4_overlap import RQ4Overlap
#from .rq4 import RQ4Correlation
#from .rq5 import RQ5BlindSpots

__all__ = [
    "Analyzer", "AnalysisContext", "AnalysisResult",
    "RQ1Contribution", 
    "RQ3Modularity", 
    "RQ4Overlap", 
#    "RQ4Correlation", 
#    "RQ5BlindSpots",
]


# Register analyzer *classes* (not instances)
_REG: Dict[str, Type[Analyzer]] = {
    "rq1": RQ1Contribution,
    "rq3": RQ3Modularity,
    "rq4": RQ4Overlap,
    # ...
}

def all_analyzers() -> List[Type["Analyzer"]]:
    return [_REG[k] for k in sorted(_REG.keys())]

def select(keys: Optional[Sequence[str]] = None) -> List[Type["Analyzer"]]:
    """
    If keys is None or empty -> return all analyzers.
    Otherwise -> return analyzers in the order of keys.
    """
    if not keys:
        return all_analyzers()

    out: List[Type["Analyzer"]] = []
    for k in keys:
        if k not in _REG:
            raise KeyError(f"Unknown analyzer '{k}'. Available: {sorted(_REG.keys())}")
        out.append(_REG[k])
    return out