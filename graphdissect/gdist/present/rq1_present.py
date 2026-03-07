from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .present import Present


class RQ1Present(Present):
    """
    RQ1 (executable-level union summary only):
    Does combining multiple drivers yield strictly greater union structural coverage
    than the best single driver under equivalent total fuzzing budgets?

    Current scope:
      - This presenter does NOT compare against true single-driver full-budget baselines.
      - It only reports executable-level union structural coverage aggregated across drivers.

    Input:
      - tables/rq1_contrib__summary.csv

    Required columns:
      bench, exe, exe_dir, num_drivers,
      sum_cg_node_own, sum_cg_edge_own, sum_cfg_edge_own, sum_bug_count

    Output:
      - rq1_present__exe_summary.csv
    """

    name = "rq1"
    required_files = (
        "rq1_contrib__summary.csv",
    )

    @staticmethod
    def _dedup_summary(summ: pd.DataFrame) -> pd.DataFrame:
        key = ["bench", "exe"]
        required = [
            "num_drivers",
            "sum_cg_node_own",
            "sum_cg_edge_own",
            "sum_cfg_edge_own",
            "sum_bug_count",
        ]
        missing = [c for c in key + required if c not in summ.columns]
        if missing:
            raise KeyError(f"rq1_contrib__summary.csv missing columns: {missing}")

        dup_mask = summ.duplicated(subset=key, keep=False)
        if not dup_mask.any():
            return summ

        dups = summ.loc[dup_mask].copy()
        bad = []
        for (b, e), g in dups.groupby(key, sort=False):
            uniq = g[required].apply(lambda r: tuple(r.tolist()), axis=1).unique()
            if len(uniq) != 1:
                cols_show = key + required + ([c for c in ["exe_dir"] if c in g.columns])
                bad.append((b, e, g[cols_show]))

        if bad:
            b, e, gshow = bad[0]
            raise ValueError(
                "rq1_contrib__summary.csv has conflicting duplicate rows for the same (bench, exe). "
                f"First conflict: bench={b}, exe={e}\n"
                f"{gshow.to_string(index=False)}"
            )

        return summ.drop_duplicates(subset=key, keep="first")

    def _apply_pair_order(
        self,
        df: pd.DataFrame,
        pair_order: dict[tuple[str, str], int],
    ) -> pd.DataFrame:
        df = df.copy()
        df["_pair_ord"] = df.apply(
            lambda r: pair_order.get((r["bench"], r["exe"]), 10**9),
            axis=1,
        )
        df = df.sort_values(["_pair_ord", "bench", "exe"], kind="mergesort")
        return df.drop(columns=["_pair_ord"])

    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        summ = self._load_concat("rq1_contrib__summary.csv")
        summ = self._dedup_summary(summ)

        cols = [
            "bench",
            "exe",
            "num_drivers",
            "sum_cg_node_own",
            "sum_cg_edge_own",
            "sum_cfg_edge_own",
            "sum_bug_count",
        ]
        out = summ[cols].copy()

        out = out.rename(
            columns={
                "num_drivers": "#Driver",
                "sum_cg_node_own": "#CGNode",
                "sum_cg_edge_own": "#CGEdge",
                "sum_cfg_edge_own": "#CFGEdge",
                "sum_bug_count": "#Bug",
            }
        )

        pair_order = self._build_bench_order()
        out = self._apply_pair_order(out, pair_order)
        out.to_csv(out_dir / "rq1_present__exe_summary.csv", index=False)
