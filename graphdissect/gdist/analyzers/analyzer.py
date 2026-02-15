# gdist/analyzers/analyzer.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from graph.graph import DrvGraph


@dataclass
class AnalysisContext:
    # directory of a bench, e.g., "bench/exp1"
    benchDir: Path

    # driver metadata
    drvGraph: DrvGraph = field(default_factory=DrvGraph)


@dataclass
class AnalysisResult:
    tables: Dict[str, pd.DataFrame] = field(default_factory=dict)
    artifacts: Dict[str, Path] = field(default_factory=dict)


class Analyzer:
    """
    Base Analyzer API: implement compute(), and you get run()+write_tables() for free.
    """
    key: str = "base"
    description: str = "base analyzer"

    def run(self, ctx: AnalysisContext) -> AnalysisResult:
        self._ensure_out(ctx)
        res = self.compute(ctx)
        self.write_tables(ctx, res)
        return res

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        raise NotImplementedError

    def write_tables(self, ctx: AnalysisContext, res: AnalysisResult) -> None:
        tables_dir = ctx.out_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
        for name, df in res.tables.items():
            out = tables_dir / f"{self.key}__{name}.csv"
            df.to_csv(out, index=False)

    def _ensure_out(self, ctx: AnalysisContext) -> None:
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        (ctx.out_dir / "tables").mkdir(parents=True, exist_ok=True)
        (ctx.out_dir / "plots").mkdir(parents=True, exist_ok=True)
