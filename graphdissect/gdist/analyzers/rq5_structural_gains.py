from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import pandas as pd

from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult

EdgeKey = Tuple[int, int]


class RQ5StructuralGains(Analyzer):
    pass