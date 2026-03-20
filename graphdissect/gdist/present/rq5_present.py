from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from .present import Present


class RQ5Present(Present):
    """
    RQ5 (final-only): Residual under-explored structural regions after
    union multi-driver fuzzing.
    """

    name = "rq5"
    required_files = (
        "rq5__summary.csv",
        "rq5__regions.csv",
        "rq5__region_distribution.csv",
        "rq5__candidate_gaps.csv",
        "rq5__region_functions.csv",
    )

    exe_rename: Dict[str, str] = None

    def __post_init__(self):
        if self.exe_rename is None:
            self.exe_rename = {"unbound-checkconf": "checkconf"}

    def _apply_pair_order(
        self,
        df: pd.DataFrame,
        pair_order: Dict[Tuple[str, str], int],
        extra_sort: List[str] | None = None,
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame() if df is None else df

        out = df.copy()
        out["_pair_ord"] = out.apply(
            lambda r: pair_order.get((str(r["bench"]), str(r["exe"])), 10**9),
            axis=1,
        )
        sort_cols = ["_pair_ord", "bench", "exe"]
        if extra_sort:
            sort_cols.extend(extra_sort)
        out = out.sort_values(sort_cols, kind="mergesort")
        return out.drop(columns=["_pair_ord"])

    # -----------------------------
    # main
    # -----------------------------
    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df_summary = self._normalize_frames(self._load_concat("rq5__summary.csv"))
        df_regions = self._normalize_frames(self._load_concat("rq5__regions.csv"))
        df_dist = self._normalize_frames(self._load_concat("rq5__region_distribution.csv"))
        df_gaps = self._normalize_frames(self._load_concat("rq5__candidate_gaps.csv"))
        df_funcs = self._normalize_frames(self._load_concat("rq5__region_functions.csv"))

        pair_order = self._build_bench_order()

        # Table 1: distribution/summary
        tab_summary = self.build_rq5_region_coverage_summary_table(df_dist)
        if not tab_summary.empty:
            tab_summary = self._apply_pair_order(tab_summary, pair_order=pair_order)
        tab_summary.to_csv(out_dir / "rq5_present__region_coverage_summary.csv", index=False)

        # Table 2: candidate gaps
        tab_gaps = self.build_rq5_candidate_gaps_table(
            df_gaps=df_gaps,
            df_funcs=df_funcs,
            top_k_per_exe=3,
            preview_n=8,
        )
        if not tab_gaps.empty:
            tab_gaps = self._apply_pair_order(
                tab_gaps,
                pair_order=pair_order,
                extra_sort=["gap_rank", "region_id"],
            )
        tab_gaps.to_csv(out_dir / "rq5_present__candidate_gaps.csv", index=False)

        # Table 3: full function list for selected gaps
        tab_gap_funcs = self.build_rq5_candidate_gap_functions_table(
            df_gaps=df_gaps,
            df_funcs=df_funcs,
            top_k_per_exe=3,
        )
        if not tab_gap_funcs.empty:
            tab_gap_funcs = self._apply_pair_order(
                tab_gap_funcs,
                pair_order=pair_order,
                extra_sort=["gap_rank", "region_id"],
            )
        tab_gap_funcs.to_csv(out_dir / "rq5_present__candidate_gap_functions.csv", index=False)

        # Optional normalized raw tables
        if not df_summary.empty:
            df_summary = self._apply_pair_order(df_summary, pair_order=pair_order)
        if not df_regions.empty:
            df_regions = self._apply_pair_order(
                df_regions,
                pair_order=pair_order,
                extra_sort=["region_id"],
            )
        if not df_dist.empty:
            df_dist = self._apply_pair_order(df_dist, pair_order=pair_order)
        if not df_gaps.empty:
            df_gaps = self._apply_pair_order(
                df_gaps,
                pair_order=pair_order,
                extra_sort=["gap_rank", "region_id"],
            )
        if not df_funcs.empty:
            df_funcs = self._apply_pair_order(
                df_funcs,
                pair_order=pair_order,
                extra_sort=["region_id"],
            )

        df_summary.to_csv(out_dir / "rq5_present__summary.csv", index=False)
        df_regions.to_csv(out_dir / "rq5_present__regions.csv", index=False)
        df_dist.to_csv(out_dir / "rq5_present__region_distribution.csv", index=False)
        df_gaps.to_csv(out_dir / "rq5_present__candidate_gaps_raw.csv", index=False)
        df_funcs.to_csv(out_dir / "rq5_present__region_functions.csv", index=False)

    def post_run(self) -> None:
        return None

    # -----------------------------
    # Normalize
    # -----------------------------
    def _normalize_frames(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()
        exe_rename = self.exe_rename or {"unbound-checkconf": "checkconf"}

        if "bench" in out.columns:
            out["bench"] = out["bench"].astype(str)
        if "exe" in out.columns:
            out["exe"] = out["exe"].astype(str).map(lambda s: exe_rename.get(s, s))

        numeric_cols = [
            "backbone_nodes",
            "backbone_edges",
            "union_covered_nodes",
            "union_coverage",
            "num_regions",
            "region_id",
            "region_size",
            "covered_nodes",
            "uncovered_nodes",
            "region_coverage",
            "internal_cg_edges",
            "boundary_out_edges",
            "boundary_in_edges",
            "gap_rank",
            "rc_min",
            "rc_p25",
            "rc_median",
            "rc_p75",
            "rc_p90",
            "rc_max",
            "share_rc_eq_0",
            "share_rc_le_0_1",
            "share_rc_le_0_2",
            "share_rc_le_0_5",
        ]
        for c in numeric_cols:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")

        return out

    # -----------------------------
    # Helpers
    # -----------------------------
    @staticmethod
    def _preview_function_names(s: str, n: int = 8) -> str:
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
        parts = [x.strip() for x in str(s).split(";") if x.strip()]
        if not parts:
            return ""
        if len(parts) <= n:
            return "; ".join(parts)
        return "; ".join(parts[:n]) + f"; ... (+{len(parts) - n} more)"

    @staticmethod
    def _select_top_k_per_exe(df: pd.DataFrame, k: int) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame() if df is None else df

        out = df.copy()
        if "gap_rank" not in out.columns or out["gap_rank"].isna().all():
            out = out.sort_values(
                by=["bench", "exe", "region_coverage", "uncovered_nodes", "region_size"],
                ascending=[True, True, True, False, False],
                kind="mergesort",
            )
            out["gap_rank"] = out.groupby(["bench", "exe"], sort=False).cumcount() + 1

        out = out.sort_values(
            by=["bench", "exe", "gap_rank", "region_id"],
            ascending=[True, True, True, True],
            kind="mergesort",
        )
        return out.groupby(["bench", "exe"], sort=False).head(k).reset_index(drop=True)

    # -----------------------------
    # Table 1: region coverage summary
    # -----------------------------
    def build_rq5_region_coverage_summary_table(self, df_dist: pd.DataFrame) -> pd.DataFrame:
        if df_dist is None or df_dist.empty:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "num_regions",
                    "rc_min",
                    "rc_p25",
                    "rc_median",
                    "rc_p75",
                    "rc_p90",
                    "rc_max",
                    "share_rc_eq_0",
                    "share_rc_le_0_1",
                    "share_rc_le_0_2",
                    "share_rc_le_0_5",
                ]
            )

        cols = [
            "bench",
            "exe",
            "num_regions",
            "rc_min",
            "rc_p25",
            "rc_median",
            "rc_p75",
            "rc_p90",
            "rc_max",
            "share_rc_eq_0",
            "share_rc_le_0_1",
            "share_rc_le_0_2",
            "share_rc_le_0_5",
        ]
        keep = [c for c in cols if c in df_dist.columns]
        out = df_dist[keep].copy()

        for c in out.columns:
            if c.startswith("rc_") or c.startswith("share_"):
                out[c] = pd.to_numeric(out[c], errors="coerce").round(3)

        return out

    # -----------------------------
    # Table 2: candidate gaps
    # -----------------------------
    def build_rq5_candidate_gaps_table(
        self,
        df_gaps: pd.DataFrame,
        df_funcs: pd.DataFrame,
        top_k_per_exe: int = 3,
        preview_n: int = 8,
    ) -> pd.DataFrame:
        if df_gaps is None or df_gaps.empty:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "gap_rank",
                    "region_id",
                    "region_size",
                    "covered_nodes",
                    "uncovered_nodes",
                    "region_coverage",
                    "function_preview",
                ]
            )

        gaps = self._select_top_k_per_exe(df_gaps, top_k_per_exe)

        if df_funcs is not None and not df_funcs.empty:
            func_keep = [c for c in ["bench", "exe", "region_id", "function_names"] if c in df_funcs.columns]
            funcs = df_funcs[func_keep].copy()
            gaps = gaps.merge(funcs, on=["bench", "exe", "region_id"], how="left")
            gaps["function_preview"] = gaps["function_names"].map(
                lambda s: self._preview_function_names(s, n=preview_n)
            )
        else:
            gaps["function_preview"] = ""

        keep = [
            c for c in [
                "bench",
                "exe",
                "gap_rank",
                "region_id",
                "region_size",
                "covered_nodes",
                "uncovered_nodes",
                "region_coverage",
                "internal_cg_edges",
                "boundary_out_edges",
                "boundary_in_edges",
                "function_preview",
            ] if c in gaps.columns
        ]
        out = gaps[keep].copy()

        if "region_coverage" in out.columns:
            out["region_coverage"] = pd.to_numeric(out["region_coverage"], errors="coerce").round(3)

        return out

    # -----------------------------
    # Table 3: full function lists
    # -----------------------------
    def build_rq5_candidate_gap_functions_table(
        self,
        df_gaps: pd.DataFrame,
        df_funcs: pd.DataFrame,
        top_k_per_exe: int = 3,
    ) -> pd.DataFrame:
        if df_gaps is None or df_gaps.empty or df_funcs is None or df_funcs.empty:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "gap_rank",
                    "region_id",
                    "region_size",
                    "region_coverage",
                    "function_ids",
                    "function_names",
                ]
            )

        gaps = self._select_top_k_per_exe(df_gaps, top_k_per_exe)

        func_keep = [c for c in ["bench", "exe", "region_id", "function_ids", "function_names"] if c in df_funcs.columns]
        funcs = df_funcs[func_keep].copy()

        out = gaps.merge(funcs, on=["bench", "exe", "region_id"], how="left")

        keep = [
            c for c in [
                "bench",
                "exe",
                "gap_rank",
                "region_id",
                "region_size",
                "covered_nodes",
                "uncovered_nodes",
                "region_coverage",
                "function_ids",
                "function_names",
            ] if c in out.columns
        ]
        out = out[keep].copy()

        if "region_coverage" in out.columns:
            out["region_coverage"] = pd.to_numeric(out["region_coverage"], errors="coerce").round(3)

        return out