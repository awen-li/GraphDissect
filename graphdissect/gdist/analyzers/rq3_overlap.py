from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import pandas as pd
from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


class RQ3Overlap(Analyzer):
    key = "rq3"
    description = "RQ3: pairwise overlap (IoU) among driver-induced subgraphs + redundancy vs coverage growth"

    def __init__(self, max_pairs: int = 200_000, top_k_pairs: int = 30):
        self.max_pairs = max_pairs
        self.top_k_pairs = top_k_pairs

        self.func_cov: Dict[int, Set[str]] = {}
        self.edges_total: Dict[int, int] = {}
        self.edges_delta: Dict[int, int] = {}

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        g = ctx.ensure_drvgraph()
        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        # (1) per-driver covered function sets
        self.func_cov = self._compute_function_coverage(g)

        # (2) per-driver coverage growth proxy (from driver_runtimes/<id>)
        self.edges_total, self.edges_delta = self._parse_edges_runtime(exe_dir, g)

        # (3) driver table (sizes + growth metrics)
        df_drivers = self._build_driver_table(exe_dir, g, bench_name, exe_name)

        # (4) pairwise IoU table
        df_pairs = self._compute_pairwise_iou(bench_name, exe_name, df_drivers)

        # (5) distribution summary + top pairs
        df_dist = self._build_iou_distribution(bench_name, exe_name, df_pairs)
        df_top = self._top_overlapping_pairs(df_pairs)

        # (6) overlap vs growth (per-driver aggregation + correlations)
        df_driver_overlap = self._aggregate_driver_overlap(bench_name, exe_name, df_pairs, df_drivers)
        df_corr = self._overlap_growth_correlation(bench_name, exe_name, df_driver_overlap)

        return AnalysisResult(tables={
            "drivers": df_drivers,
            "pairs_iou": df_pairs,
            "iou_distribution": df_dist,
            "top_overlapping_pairs": df_top,
            "driver_overlap": df_driver_overlap,
            "overlap_vs_growth": df_corr,
        })

    # ----------------------------
    # (1) Function coverage (nodes)
    # ----------------------------
    def _compute_function_coverage(self, g) -> Dict[int, Set[str]]:
        out: Dict[int, Set[str]] = {}
        for drv_id in g.drvList.keys():
            did = int(drv_id)
            cov_functions = g.get_driver_graph(drv_id)  # must exist
            out[did] = set(map(str, cov_functions))
        return out

    # ----------------------------
    # (2) Parse runtime (edges total + delta)
    # ----------------------------
    def _parse_edges_runtime(self, exe_dir: Path, g) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Parse driver_runtimes/<driver_id> lines like:
          edges:1379(+0), crashes:0(+0), time:4265, exes:13

        Returns:
          edges_total[did] = 1379
          edges_delta[did] = 0   (if present, else 0)
        """
        rt_dir = exe_dir / "driver_runtimes"

        # capture edges_total and optional (+delta)
        edges_re = re.compile(r"\bedges\s*:\s*(\d+)(?:\s*\(\s*([+-]?\d+)\s*\))?")

        total: Dict[int, int] = {}
        delta: Dict[int, int] = {}

        for drv_id in g.drvList.keys():
            did = int(drv_id)
            p = rt_dir / str(did)
            if not p.is_file():
                total[did] = 0
                delta[did] = 0
                continue

            s = p.read_text(errors="ignore")
            m = edges_re.search(s)
            if not m:
                total[did] = 0
                delta[did] = 0
                continue

            total[did] = int(m.group(1))
            delta[did] = int(m.group(2)) if m.group(2) is not None else 0

        return total, delta

    # ----------------------------
    # (3) Driver table
    # ----------------------------
    def _build_driver_table(self, exe_dir: Path, g, bench_name: str, exe_name: str) -> pd.DataFrame:
        # driver order if you have it; else fallback
        order: List[int] = []
        try:
            drivers_dir = exe_dir / "drivers"
            order = _load_driver_order(drivers_dir)  # your helper, if present
        except Exception:
            order = []
        if not order:
            order = [int(k) for k in g.drvList.keys()]

        rows: List[Dict[str, object]] = []
        for did in order:
            nodes = self.func_cov.get(did, set())
            drv = g.drvList.get(did) or g.drvList.get(str(did))
            drv_name = getattr(drv, "name", str(did)) if drv is not None else str(did)

            rows.append({
                "bench": bench_name,
                "exe": exe_name,
                "driver_id": int(did),
                "driver_name": drv_name,
                "func_total": int(len(nodes)),
                "edges_total": int(self.edges_total.get(did, 0)),
                "edges_delta": int(self.edges_delta.get(did, 0)),  # growth proxy if (+delta) is meaningful
            })

        return pd.DataFrame(rows)

    # ----------------------------
    # (4) Pairwise IoU
    # ----------------------------
    def _compute_pairwise_iou(self, bench: str, exe: str, df_drivers: pd.DataFrame) -> pd.DataFrame:
        if df_drivers.empty:
            return pd.DataFrame(columns=[
                "bench", "exe",
                "driver_i", "driver_j",
                "name_i", "name_j",
                "size_i", "size_j",
                "inter", "union", "iou",
            ])

        ids = df_drivers["driver_id"].astype(int).tolist()
        names = dict(zip(df_drivers["driver_id"].astype(int), df_drivers["driver_name"].astype(str)))

        n = len(ids)
        num_pairs = n * (n - 1) // 2
        if num_pairs > self.max_pairs:
            # If you ever scale up hugely, cap pairs deterministically (first K pairs)
            # (You can later replace with sampling.)
            cap_n = int((1 + (1 + 8 * self.max_pairs) ** 0.5) / 2)
            ids = ids[:max(2, cap_n)]
            n = len(ids)

        rows: List[Dict[str, object]] = []
        for a in range(n):
            i = ids[a]
            si = self.func_cov.get(i, set())
            for b in range(a + 1, n):
                j = ids[b]
                sj = self.func_cov.get(j, set())
                if not si and not sj:
                    inter = 0
                    union = 0
                    iou = 0.0
                else:
                    inter = len(si & sj)
                    union = len(si | sj)
                    iou = (inter / union) if union > 0 else 0.0

                rows.append({
                    "bench": bench,
                    "exe": exe,
                    "driver_i": int(i),
                    "driver_j": int(j),
                    "name_i": names.get(i, str(i)),
                    "name_j": names.get(j, str(j)),
                    "size_i": int(len(si)),
                    "size_j": int(len(sj)),
                    "inter": int(inter),
                    "union": int(union),
                    "iou": float(iou),
                })

        return pd.DataFrame(rows)

    # ----------------------------
    # (5) Distribution + top pairs
    # ----------------------------
    def _build_iou_distribution(self, bench: str, exe: str, df_pairs: pd.DataFrame) -> pd.DataFrame:
        if df_pairs.empty:
            return pd.DataFrame([{
                "bench": bench, "exe": exe,
                "num_pairs": 0,
            }])

        s = df_pairs["iou"]
        return pd.DataFrame([{
            "bench": bench,
            "exe": exe,
            "num_pairs": int(len(df_pairs)),
            "iou_min": float(s.min()),
            "iou_p25": float(s.quantile(0.25)),
            "iou_median": float(s.quantile(0.50)),
            "iou_p75": float(s.quantile(0.75)),
            "iou_p90": float(s.quantile(0.90)),
            "iou_p99": float(s.quantile(0.99)),
            "iou_max": float(s.max()),
            "share_iou_ge_0_5": float((s >= 0.5).mean()),
            "share_iou_ge_0_8": float((s >= 0.8).mean()),
        }])

    def _top_overlapping_pairs(self, df_pairs: pd.DataFrame) -> pd.DataFrame:
        if df_pairs.empty:
            return pd.DataFrame(columns=df_pairs.columns)
        cols = ["bench", "exe", "driver_i", "driver_j", "name_i", "name_j", "size_i", "size_j", "inter", "union", "iou"]
        return df_pairs.sort_values("iou", ascending=False).head(self.top_k_pairs)[cols].copy()

    # ----------------------------
    # (6) Overlap vs growth
    # ----------------------------
    def _aggregate_driver_overlap(self, bench: str, exe: str, df_pairs: pd.DataFrame, df_drivers: pd.DataFrame) -> pd.DataFrame:
        """
        For each driver d:
          avg_iou(d) over all pairs involving d
          max_iou(d)
        Then attach growth proxies (edges_total, edges_delta, func_total).
        """
        if df_drivers.empty:
            return pd.DataFrame(columns=[
                "bench", "exe", "driver_id", "driver_name",
                "func_total", "edges_total", "edges_delta",
                "avg_iou", "max_iou", "num_pairs",
            ])

        base = df_drivers.copy()
        base["driver_id"] = base["driver_id"].astype(int)

        if df_pairs.empty:
            base["avg_iou"] = 0.0
            base["max_iou"] = 0.0
            base["num_pairs"] = 0
            return base[[
                "bench", "exe", "driver_id", "driver_name",
                "func_total", "edges_total", "edges_delta",
                "avg_iou", "max_iou", "num_pairs",
            ]]

        # explode pairs into per-driver rows
        left = df_pairs[["driver_i", "iou"]].rename(columns={"driver_i": "driver_id"})
        right = df_pairs[["driver_j", "iou"]].rename(columns={"driver_j": "driver_id"})
        both = pd.concat([left, right], ignore_index=True)
        both["driver_id"] = both["driver_id"].astype(int)

        agg = both.groupby("driver_id").agg(
            avg_iou=("iou", "mean"),
            max_iou=("iou", "max"),
            num_pairs=("iou", "count"),
        ).reset_index()

        out = base.merge(agg, on="driver_id", how="left")
        out["avg_iou"] = out["avg_iou"].fillna(0.0)
        out["max_iou"] = out["max_iou"].fillna(0.0)
        out["num_pairs"] = out["num_pairs"].fillna(0).astype(int)

        return out[[
            "bench", "exe", "driver_id", "driver_name",
            "func_total", "edges_total", "edges_delta",
            "avg_iou", "max_iou", "num_pairs",
        ]]

    def _overlap_growth_correlation(self, bench: str, exe: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Correlate overlap (avg_iou / max_iou) with growth proxies (edges_delta, edges_total, func_total).
        Uses pandas corr (Pearson).
        """
        if df.empty:
            return pd.DataFrame(columns=["bench", "exe", "x", "y", "pearson_r"])

        # choose the best available growth proxy:
        # edges_delta (if non-trivial), else edges_total
        use_delta = df["edges_delta"].abs().sum() > 0
        growth_col = "edges_delta" if use_delta else "edges_total"

        rows = []
        for x in ["avg_iou", "max_iou"]:
            for y in [growth_col, "func_total"]:
                r = df[[x, y]].corr(method="pearson").iloc[0, 1]
                rows.append({
                    "bench": bench,
                    "exe": exe,
                    "x": x,
                    "y": y,
                    "pearson_r": float(r) if pd.notna(r) else 0.0,
                })

        # Also output which growth proxy we used
        rows.append({
            "bench": bench,
            "exe": exe,
            "x": "growth_proxy",
            "y": growth_col,
            "pearson_r": 0.0,
        })

        return pd.DataFrame(rows)

