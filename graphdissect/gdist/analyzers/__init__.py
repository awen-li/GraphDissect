# gdist/analyzers/__init__.py
from .analyzer import Analyzer, AnalysisContext, AnalysisResult

# bring analyzers into registry
#from .rq1 import RQ1Contribution
#from .rq2 import RQ2Modularity
#from .rq3 import RQ3Overlap
#from .rq4 import RQ4Correlation
#from .rq5 import RQ5BlindSpots

__all__ = [
    "Analyzer", "AnalysisContext", "AnalysisResult",
#    "RQ1Contribution", 
#    "RQ2Modularity", 
#    "RQ3Overlap", 
#    "RQ4Correlation", 
#    "RQ5BlindSpots",
]
