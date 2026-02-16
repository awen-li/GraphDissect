from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
import pandas as pd
from gdist.graph.graph import DrvGraph
from gdist.registry import register


@dataclass
class AnalysisContext:
    """
    benchDir: executable directory, e.g. benchmarks/libxml2/xmllint
    drvGraph: loaded driver graph for this executable (lazy or eager)
    """
    benchDir: Path
    drvGraph: Optional[DrvGraph] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.ensure_drvgraph()

    def ensure_drvgraph(self) -> DrvGraph:
        if self.drvGraph is not None:
            return self.drvGraph

        benchPath = self.benchDir.parent   # benchmarks/libxml2
        binaryName = self.benchDir.name    # xmllint

        g = DrvGraph(benchPath=benchPath, binaryName=binaryName)
        g._load(strict=False)
        self.drvGraph = g
        return g



@dataclass
class AnalysisResult:
    tables: Dict[str, pd.DataFrame] = field(default_factory=dict)
    artifacts: Dict[str, Path] = field(default_factory=dict)

@register
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

            # track artifact path for downstream usage
            res.artifacts[f"table:{name}"] = out

    def _ensure_out(self, ctx: AnalysisContext) -> None:
        ctx.out_dir.mkdir(parents=True, exist_ok=True)
        (ctx.out_dir / "tables").mkdir(parents=True, exist_ok=True)
        (ctx.out_dir / "plots").mkdir(parents=True, exist_ok=True)
