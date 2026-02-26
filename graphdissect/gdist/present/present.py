from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class BenchTables:
    """A single executable's tables directory (e.g., benchmarks/binutils/objdump/tables)."""
    bench_key: str          # "binutils/objdump"
    exe: str                # "objdump"
    tables_dir: Path


class Present:
    """
    Base presenter.
    - discovers benchmarks/*/*/tables
    - provides IO helpers
    - provides LaTeX rendering helpers (booktabs)
    """

    # Subclasses override these
    name: str = "present"
    required_files: Tuple[str, ...] = ()

    def __init__(self, benchs, suite_dir: Path, out_dir: Path | None = None):
        self.benchs = benchs
        self.suite_dir = Path(suite_dir)
        
        # default output dir: <suite_dir>/paper_artifacts/<rq_name>/
        if out_dir is None:
            out_dir = self.suite_dir / "paper_artifacts" / self.name
        
        self.out_dir = Path(out_dir)
        self.fig_dir = self.out_dir / "figs"
        self.tex_dir = self.out_dir / "tables"
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self.tex_dir.mkdir(parents=True, exist_ok=True)

    def discover_tables(self) -> Dict[str, BenchTables]:
        """
        Find all tables/ dirs under suite_dir.
        Returns mapping bench_key -> BenchTables
        """
        out: Dict[str, BenchTables] = {}

        for bench in self.benchs:
            bench_dir = Path(bench)
            tdir = bench_dir / "tables"
            if not tdir.is_dir():
                continue

            bench_key = bench_dir.name
            exe = bench_key   
            out[bench_key] = BenchTables(bench_key=bench_key, exe=exe, tables_dir=tdir)

        return out

    def validate_tables(self, t: BenchTables) -> bool:
        """Check required files exist for this presenter."""
        for fn in self.required_files:
            if not (t.tables_dir / fn).exists():
                return False
        return True

    # ---------- CSV helpers ----------
    def read_csv(self, t: BenchTables, filename: str) -> pd.DataFrame:
        p = t.tables_dir / filename
        if not p.exists():
            raise FileNotFoundError(str(p))
        return pd.read_csv(p)

    # ---------- LaTeX helpers ----------
    def to_booktabs(
        self,
        df: pd.DataFrame,
        columns: List[str],
        headers: Optional[List[str]] = None,
        caption: str = "",
        label: str = "",
        align: Optional[str] = None,
        size: str = "\\small",
    ) -> str:
        """
        Convert df[columns] into a booktabs LaTeX table string.
        """
        if headers is None:
            headers = columns
        if align is None:
            align = "l" + "r" * (len(columns) - 1)

        def fmt(x) -> str:
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return "-"
            if isinstance(x, float):
                return f"{x:.3f}"
            return str(x)

        lines: List[str] = []
        lines.append("\\begin{table}[t]")
        lines.append("\\centering")
        if size:
            lines.append(size)
        lines.append(f"\\begin{{tabular}}{{{align}}}")
        lines.append("\\toprule")
        lines.append(" & ".join(headers) + " \\\\")
        lines.append("\\midrule")
        for _, row in df.iterrows():
            vals = [fmt(row.get(c, None)) for c in columns]
            lines.append(" & ".join(vals) + " \\\\")
        lines.append("\\bottomrule")
        lines.append("\\end{tabular}")
        if caption:
            lines.append(f"\\caption{{{caption}}}")
        if label:
            lines.append(f"\\label{{{label}}}")
        lines.append("\\end{table}")
        return "\n".join(lines)

    def write_tex(self, filename: str, content: str) -> Path:
        p = self.tex_dir / filename
        p.write_text(content)
        return p

    def _build_bench_order(self) -> dict[tuple[str, str], int]:
        """
        self.benchs is a list of bench directories like:
        /.../benchmarks/binutils/addr2line

        We map:
        bench = parent dir name  -> binutils
        exe   = leaf dir name    -> addr2line
        """
        order: dict[tuple[str, str], int] = {}
        for i, p in enumerate(getattr(self, "benchs", []) or []):
            bp = Path(p)
            bench = bp.parent.name
            exe = bp.name
            order[(bench, exe)] = i
        return order

    # ---------- API ----------
    def run(self) -> None:
        """
        Subclasses implement this:
        - load all benches
        - generate tex + figs
        """
        raise NotImplementedError