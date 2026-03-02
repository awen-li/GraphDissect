from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd

from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


EdgeKey = Tuple[int, int]


class RQ4Overlap(Analyzer):
    """
    RQ4: Pairwise overlap and redundancy among driver-induced subgraphs
         measured at call-graph level.

    Metrics:
      - IoU_V over covered function sets (call-graph nodes)
      - IoU_E over covered call edges (call-graph edges)

    Notes:
      - We intentionally ignore CFG-edge counters in driver_runtimes/<id>.
      - Optional projection onto a shared whole-program call-graph backbone.
    """

    key = "rq4"
    description = "RQ4: pairwise overlap (IoU_V / IoU_E) among driver-induced call-graph subgraphs"

    def __init__(self, max_pairs: int = 200_000, top_k_pairs: int = 25, project_to_backbone: bool = True):
        self.max_pairs = int(max_pairs)
        self.top_k_pairs = int(top_k_pairs)
        self.project_to_backbone = bool(project_to_backbone)

        self.func_cov: Dict[int, Set[int]] = {}
        self.edge_cov: Dict[int, Set[EdgeKey]] = {}

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        g = ctx.ensure_drvgraph()
        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        backbone_edge_set = self._load_backbone_edge_set(g) if self.project_to_backbone else None

        # (1) coverage sets at call-graph level
        self.func_cov, self.edge_cov = self._compute_driver_cov_sets(g, backbone_edge_set)

        # (2) driver table (callgraph sizes only)
        df_drivers = self._build_driver_table(g, bench_name, exe_name)

        # (3) pairwise IoU table (V + E)
        df_pairs = self._compute_pairwise_iou(bench_name, exe_name, df_drivers)

        # (4) distribution summary + top pairs
        df_dist = self._build_iou_distribution(bench_name, exe_name, df_pairs)
        df_top_v, df_top_e = self._top_overlapping_pairs(df_pairs)

        # (5) per-driver overlap aggregates
        df_driver_overlap = self._aggregate_driver_overlap(bench_name, exe_name, df_pairs, df_drivers)

        return AnalysisResult(
            tables={
                "drivers": df_drivers,
                "pairs_iou": df_pairs,
                "iou_distribution": df_dist,
                "top_overlapping_pairs_v": df_top_v,
                "top_overlapping_pairs_e": df_top_e,
                "driver_overlap": df_driver_overlap,
            }
        )

    # ----------------------------
    # Backbone (whole-program call graph)
    # ----------------------------
    def _load_backbone_edge_set(self, g) -> Set[EdgeKey]:
        """
        Shared reference call graph (projection backbone).
        g.get_whole_graph() -> (nodes, edges)
        """
        _, edges = g.get_whole_graph()
        out: Set[EdgeKey] = set()
        for (u, v) in edges:
            iu, iv = int(u), int(v)
            if iu != iv:
                out.add((iu, iv))
        return out

    # ----------------------------
    # Per-driver call-graph coverage sets
    # ----------------------------
    def _compute_driver_cov_sets(
        self, g, backbone_edge_set: Set[EdgeKey] | None
    ) -> Tuple[Dict[int, Set[int]], Dict[int, Set[EdgeKey]]]:
        """
        Uses: g.get_driver_graph(drv_id) -> (nodes, edges)
        Returns:
          func_cov[did] = V_d
          edge_cov[did] = E_d (optionally projected to backbone)
        """
        func_cov: Dict[int, Set[int]] = {}
        edge_cov: Dict[int, Set[EdgeKey]] = {}

        for drv_id in g.drvList.keys():
            did = int(drv_id)
            nodes, edges = g.get_driver_graph(drv_id)

            Vd: Set[int] = set(int(n) for n in nodes) if nodes is not None else set()
            Ed: Set[EdgeKey] = set()

            if edges is not None:
                for (u, v) in edges:
                    iu, iv = int(u), int(v)
                    if iu == iv:
                        continue
                    # keep only edges whose endpoints are in Vd (consistent G_d = (V_d, E_d))
                    if iu not in Vd or iv not in Vd:
                        continue
                    if backbone_edge_set is not None and (iu, iv) not in backbone_edge_set:
                        continue
                    Ed.add((iu, iv))

            func_cov[did] = Vd
            edge_cov[did] = Ed

        return func_cov, edge_cov

    # ----------------------------
    # Driver table
    # ----------------------------
    def _build_driver_table(self, g, bench_name: str, exe_name: str) -> pd.DataFrame:
        rows: List[Dict[str, object]] = []
        order = [int(k) for k in g.drvList.keys()]

        for did in order:
            Vd = self.func_cov.get(did, set())
            Ed = self.edge_cov.get(did, set())

            drv = g.drvList.get(did) or g.drvList.get(str(did))
            drv_name = getattr(drv, "name", str(did)) if drv is not None else str(did)

            rows.append(
                {
                    "bench": bench_name,
                    "exe": exe_name,
                    "driver_id": int(did),
                    "driver_name": str(drv_name),
                    "cg_node_total": int(len(Vd)),
                    "cg_edge_total": int(len(Ed)),
                }
            )

        return pd.DataFrame(rows)

    # ----------------------------
    # Pairwise IoU
    # ----------------------------
    @staticmethod
    def _iou(a: Set, b: Set) -> Tuple[int, int, float]:
        inter = len(a & b) if (a or b) else 0
        union = len(a | b) if (a or b) else 0
        return inter, union, (inter / union) if union > 0 else 0.0

    def _compute_pairwise_iou(self, bench: str, exe: str, df_drivers: pd.DataFrame) -> pd.DataFrame:
        if df_drivers.empty:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "driver_i",
                    "driver_j",
                    "name_i",
                    "name_j",
                    "v_inter",
                    "v_union",
                    "iou_v",
                    "e_inter",
                    "e_union",
                    "iou_e",
                ]
            )

        ids = df_drivers["driver_id"].astype(int).tolist()
        names = dict(zip(df_drivers["driver_id"].astype(int), df_drivers["driver_name"].astype(str)))

        n = len(ids)
        num_pairs = n * (n - 1) // 2
        if num_pairs > self.max_pairs:
            cap_n = int((1 + (1 + 8 * self.max_pairs) ** 0.5) / 2)
            ids = ids[: max(2, cap_n)]
            n = len(ids)

        rows: List[Dict[str, object]] = []
        for a in range(n):
            i = ids[a]
            Vi = self.func_cov.get(i, set())
            Ei = self.edge_cov.get(i, set())
            for b in range(a + 1, n):
                j = ids[b]
                Vj = self.func_cov.get(j, set())
                Ej = self.edge_cov.get(j, set())

                v_inter, v_union, iou_v = self._iou(Vi, Vj)
                e_inter, e_union, iou_e = self._iou(Ei, Ej)

                rows.append(
                    {
                        "bench": bench,
                        "exe": exe,
                        "driver_i": int(i),
                        "driver_j": int(j),
                        "name_i": names.get(i, str(i)),
                        "name_j": names.get(j, str(j)),
                        "v_inter": int(v_inter),
                        "v_union": int(v_union),
                        "iou_v": float(iou_v),
                        "e_inter": int(e_inter),
                        "e_union": int(e_union),
                        "iou_e": float(iou_e),
                    }
                )

        return pd.DataFrame(rows)

    # ----------------------------
    # Distribution summary + top pairs
    # ----------------------------
    def _build_iou_distribution(self, bench: str, exe: str, df_pairs: pd.DataFrame) -> pd.DataFrame:
        if df_pairs.empty:
            return pd.DataFrame([{"bench": bench, "exe": exe, "num_pairs": 0}])

        def summarize(col: str) -> Dict[str, float]:
            s = df_pairs[col]
            return {
                f"{col}_min": float(s.min()),
                f"{col}_p25": float(s.quantile(0.25)),
                f"{col}_median": float(s.quantile(0.50)),
                f"{col}_p75": float(s.quantile(0.75)),
                f"{col}_p90": float(s.quantile(0.90)),
                f"{col}_p99": float(s.quantile(0.99)),
                f"{col}_max": float(s.max()),
                f"share_{col}_ge_0_5": float((s >= 0.5).mean()),
                f"share_{col}_ge_0_8": float((s >= 0.8).mean()),
            }

        row: Dict[str, object] = {"bench": bench, "exe": exe, "num_pairs": int(len(df_pairs))}
        row.update(summarize("iou_v"))
        row.update(summarize("iou_e"))
        return pd.DataFrame([row])

    def _top_overlapping_pairs(self, df_pairs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if df_pairs.empty:
            empty = pd.DataFrame(columns=df_pairs.columns)
            return empty, empty

        cols = [
            "bench",
            "exe",
            "driver_i",
            "driver_j",
            "name_i",
            "name_j",
            "v_inter",
            "v_union",
            "iou_v",
            "e_inter",
            "e_union",
            "iou_e",
        ]
        top_v = df_pairs.sort_values("iou_v", ascending=False).head(self.top_k_pairs)[cols].copy()
        top_e = df_pairs.sort_values("iou_e", ascending=False).head(self.top_k_pairs)[cols].copy()
        return top_v, top_e

    # ----------------------------
    # Per-driver overlap aggregates
    # ----------------------------
    def _aggregate_driver_overlap(
        self, bench: str, exe: str, df_pairs: pd.DataFrame, df_drivers: pd.DataFrame
    ) -> pd.DataFrame:
        """
        For each driver d:
          avg/max IoU_V and avg/max IoU_E over all pairs involving d.
        """
        if df_drivers.empty:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "driver_id",
                    "driver_name",
                    "cg_node_total",
                    "cg_edge_total",
                    "avg_iou_v",
                    "max_iou_v",
                    "avg_iou_e",
                    "max_iou_e",
                    "num_pairs",
                ]
            )

        base = df_drivers.copy()
        base["driver_id"] = base["driver_id"].astype(int)

        if df_pairs.empty:
            base["avg_iou_v"] = 0.0
            base["max_iou_v"] = 0.0
            base["avg_iou_e"] = 0.0
            base["max_iou_e"] = 0.0
            base["num_pairs"] = 0
            return base[
                [
                    "bench",
                    "exe",
                    "driver_id",
                    "driver_name",
                    "cg_node_total",
                    "cg_edge_total",
                    "avg_iou_v",
                    "max_iou_v",
                    "avg_iou_e",
                    "max_iou_e",
                    "num_pairs",
                ]
            ]

        def agg_for(col: str) -> pd.DataFrame:
            left = df_pairs[["driver_i", col]].rename(columns={"driver_i": "driver_id"})
            right = df_pairs[["driver_j", col]].rename(columns={"driver_j": "driver_id"})
            both = pd.concat([left, right], ignore_index=True)
            both["driver_id"] = both["driver_id"].astype(int)
            return (
                both.groupby("driver_id")
                .agg(
                    **{
                        f"avg_{col}": (col, "mean"),
                        f"max_{col}": (col, "max"),
                        "num_pairs": (col, "count"),
                    }
                )
                .reset_index()
            )

        agg_v = agg_for("iou_v")
        agg_e = agg_for("iou_e")

        out = base.merge(agg_v, on="driver_id", how="left").merge(agg_e, on="driver_id", how="left", suffixes=("_v", "_e"))

        out["avg_iou_v"] = out["avg_iou_v"].fillna(0.0)
        out["max_iou_v"] = out["max_iou_v"].fillna(0.0)
        out["avg_iou_e"] = out["avg_iou_e"].fillna(0.0)
        out["max_iou_e"] = out["max_iou_e"].fillna(0.0)

        if "num_pairs_v" in out.columns:
            out["num_pairs"] = out["num_pairs_v"].fillna(0).astype(int)
        elif "num_pairs" in out.columns:
            out["num_pairs"] = out["num_pairs"].fillna(0).astype(int)
        else:
            out["num_pairs"] = 0

        return out[
            [
                "bench",
                "exe",
                "driver_id",
                "driver_name",
                "cg_node_total",
                "cg_edge_total",
                "avg_iou_v",
                "max_iou_v",
                "avg_iou_e",
                "max_iou_e",
                "num_pairs",
            ]
        ]
    