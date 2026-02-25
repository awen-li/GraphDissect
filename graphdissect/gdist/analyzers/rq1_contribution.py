from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Dict, List, Set
import pandas as pd
from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


class RQ1Contribution(Analyzer):
    key = "rq1_contrib"
    description = "RQ1: per-driver function/block coverage and bug discovery contributions"

    def __init__(self):
        self.cg_cov: Dict[int, Set[str]] = {}
        self.block_cov: Dict[int, int] = {}
        self.bug_cnt: Dict[int, int] = {}

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        g = ctx.ensure_drvgraph()
        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        # (1) callgraph coverage
        self.cg_cov = self._compute_callgraph_coverage(g)

        # (2) block/edge coverage
        self.block_cov = self._compute_block_coverage(exe_dir, g)

        # (3) bug contribution
        self.bug_cnt = self._compute_bug_contribution(exe_dir, g)

        df_drivers = self._build_driver_table(exe_dir, g, bench_name, exe_name)
        df_summary = self._build_summary_table(exe_dir, bench_name, exe_name, df_drivers)
        df_top = self._compute_top_contributions(df_drivers)

        return AnalysisResult(tables={
            "summary": df_summary,
            "drivers": df_drivers,
            "top_by_metric": df_top,
        })

    # ----------------------------
    # (1) callgraph coverage
    # ----------------------------
    def _compute_callgraph_coverage(self, g) -> Dict[int, Set[str]]:
        """
        get per-driver function coverage from final_marked_callgraph.dot.
        """
        out: Dict[int, Set[str]] = {}
        for drv_id in g.drvList.keys():
            # a tuple of (node_list, edge_list)
            cov_functions, cov_edges = g.get_driver_graph(drv_id)
            out[int(drv_id)] = (set(map(str, cov_functions)),
                                set(map(str, cov_edges)))
        return out

    # ----------------------------
    # (2) Block/edge coverage
    # ----------------------------
    def _compute_block_coverage(self, exe_dir: Path, g) -> Dict[int, int]:
        """
        Parse driver_runtimes/<driver_id> for 'edges:' field.
          ::: edges:1379(+0), crashes:0(+0), time:4265, exes:13
        """
        rtDir = exe_dir / "driver_runtimes"
        edges_re = re.compile(r"\bedges\s*:\s*(\d+)")

        out: Dict[int, int] = {}
        for drv_id in g.drvList.keys():
            p = rtDir / str(drv_id)
            if not p.is_file():
                out[int(drv_id)] = 0
                continue
            s = p.read_text(errors="ignore")
            m = edges_re.search(s)
            out[int(drv_id)] = int(m.group(1)) if m else 0
        return out

    # ----------------------------
    # (3) Bug contribution
    # ----------------------------
    def _compute_bug_contribution(self, exe_dir: Path, g) -> Dict[int, int]:
        """
        Parse driver_runtimes/<driver_id> for 'crashes:' field.
        Extract first integer after 'crashes:'.
        """
        rtDir = exe_dir / "driver_runtimes"
        crashes_re = re.compile(r"\bcrashes\s*:\s*(\d+)")

        out: Dict[int, int] = {}
        for drv_id in g.drvList.keys():
            p = rtDir / str(drv_id)
            if not p.is_file():
                out[int(drv_id)] = 0
                continue
            s = p.read_text(errors="ignore")
            m = crashes_re.search(s)
            out[int(drv_id)] = int(m.group(1)) if m else 0
        return out

    # ----------------------------
    # (4) Tables
    # ----------------------------
    def _build_driver_table(self, exe_dir: Path, g, bench_name: str, exe_name: str) -> pd.DataFrame:
        order = g.drvList.keys()
        order = [int(k) for k in g.drvList.keys()]

        rows: List[Dict[str, object]] = []
        for drv_id in order:
            drv = g.drvList.get(drv_id)
            drv_name = getattr(drv, "name", str(drv_id)) if drv is not None else str(drv_id)

            rows.append({
                "bench": bench_name,
                "exe": exe_name,
                "driver_id": int(drv_id),
                "driver_name": drv_name,
                "cg_node_own": len(self.cg_cov.get(int(drv_id), (set(), set()))[0]),
                "cd_edge_own": len(self.cg_cov.get(int(drv_id), (set(), set()))[1]),
                "block_own": int(self.block_cov.get(int(drv_id), 0)),
                "bug_count": int(self.bug_cnt.get(int(drv_id), 0)),
            })

        return pd.DataFrame(rows)

    def _build_summary_table(self, 
                             exe_dir: Path, 
                             bench_name: str, 
                             exe_name: str, 
                             df_drivers: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame([{
            "bench": bench_name,
            "exe": exe_name,
            "exe_dir": str(exe_dir),
            "num_drivers": int(len(df_drivers)),
            "sum_func_own": int(df_drivers["func_own"].sum()) if not df_drivers.empty else 0,
            "sum_block_own": int(df_drivers["block_own"].sum()) if not df_drivers.empty else 0,
            "sum_bug_count": int(df_drivers["bug_count"].sum()) if not df_drivers.empty else 0
        }])

    def _compute_top_contributions(self, df_drivers: pd.DataFrame) -> pd.DataFrame:
        if df_drivers.empty:
            return pd.DataFrame(columns=["metric", "bench", "exe", "driver_id", "driver_name", "value"])

        frames: List[pd.DataFrame] = []
        for metric in ["func_own", "block_own", "bug_count"]:
            t = df_drivers.sort_values(metric, ascending=False).head().copy()
            t = t[["bench", "exe", "driver_id", "driver_name", metric]]
            t = t.rename(columns={metric: "value"})
            t.insert(0, "metric", metric)
            frames.append(t)

        return pd.concat(frames, ignore_index=True)
