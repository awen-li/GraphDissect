from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .present import Present


class RQ1Present(Present):
    """
    RQ1: Does combining multiple drivers yield strictly greater union structural coverage than the best
    single driver under equivalent total fuzzing budgets?

    Input per benchmark directory:
      - tables/rq1_contrib__drivers.csv
        required columns:
          bench, exe, driver_id, driver_name, block_own, bug_count

    Output:
      - rq1_present__top_drivers.csv   (generated first)
      - (others later once union coverage source is provided)
    """

    name = "rq1"
    required_files = (
        "rq1_contrib__drivers.csv",
        "rq1_contrib__summary.csv",
        "rq1_contrib__top_by_metric.csv",
    )

    TOPN = 10

    REQUIRED_COLS = [
        "bench",
        "exe",
        "driver_id",
        "driver_name",
        "block_own",
        "bug_count",
    ]

    # -----------------------
    # IO helpers
    # -----------------------
    def _get_out_dir(self) -> Path:
        for attr in ("out_dir", "output_dir", "present_dir", "results_dir"):
            p = getattr(self, attr, None)
            if p is not None:
                return Path(p)
        return Path.cwd()

    def _write_csv(self, fname: str, df: pd.DataFrame) -> None:
        out_dir = self._get_out_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / fname, index=False)

    def _load_driver_df(self, bench_dir: str | Path) -> pd.DataFrame:
        bench_dir = Path(bench_dir)
        return pd.read_csv(bench_dir / "tables" / "rq1_contrib__drivers.csv")

    def _require_cols(self, df: pd.DataFrame, bench_dir: str | Path) -> None:
        missing = [c for c in self.REQUIRED_COLS if c not in df.columns]
        if missing:
            raise KeyError(
                f"RQ1Present: missing required columns {missing} in "
                f"{Path(bench_dir) / 'tables/rq1_contrib__drivers.csv'}; "
                f"found columns={list(df.columns)}"
            )

    # -----------------------
    # Step 0: top drivers (by block_own)
    # -----------------------
    def _top_drivers_one(self, df: pd.DataFrame) -> pd.DataFrame:
        # top within a single bench_dir file (should be one bench/exe)
        topk = df.sort_values(["block_own", "driver_id"], ascending=[False, True]).head(self.TOPN)
        return topk[
            ["bench", "exe", "driver_id", "driver_name", "block_own", "bug_count"]
        ].copy()

    # -----------------------
    # Main
    # -----------------------
    def run(self) -> None:
        print(f"RQ1Present: scanning {len(self.benchs)} benchmark dirs...")

        # 1) FIRST: collect top drivers for each benchmark dir
        top_frames: List[pd.DataFrame] = []

        for bench_dir in self.benchs:
            df = self._load_driver_df(bench_dir)
            self._require_cols(df, bench_dir)

            bench_name = str(df["bench"].iloc[0])
            exe_name = str(df["exe"].iloc[0])

            top_df = self._top_drivers_one(df)
            # keep bench_dir as an explicit key in case (bench,exe) repeats
            top_df.insert(0, "bench_dir", str(bench_dir))
            top_frames.append(top_df)

        top_all = pd.concat(top_frames, ignore_index=True) if top_frames else pd.DataFrame()
        self._write_csv("rq1_present__top_drivers.csv", top_all)
        print(f"[RQ1Present] wrote rq1_present__top_drivers.csv ({len(top_all)} rows) to {self._get_out_dir()}")

        # 2) THEN: compute RQ1 union-vs-best (needs per-driver set-level coverage source)
        # NOTE: not implemented until you tell me which table contains per-driver covered function/edge IDs.
        print("[RQ1Present] Step-0 done. Union-vs-best computation pending set-level coverage table.")
        