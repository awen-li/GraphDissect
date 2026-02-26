from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .present import Present, BenchTables


class RQ1Present(Present):
    """
    RQ1 (final-only): Driver effectiveness under equal time budgets.

    IMPORTANT (design choice):
      - We only use CFG-derived coverage for RQ1 (e.g., block coverage),
        because call-graph-derived metrics can heavily overlap and do not
        faithfully represent per-driver discovered behavior.

    Expected input (per benchmark tables_dir):
      - rq1_contrib__drivers.csv
        observed columns:
          bench, exe, driver_id, driver_name,
          block_own, bug_count

    Outputs (written to presenter output dir):
      - rq1_present__summary.csv
      - rq1_present__topk_curve.csv
      - rq1_present__cdf.csv
      - rq1_present__top_by_metric.csv
    """

    name = "rq1"
    required_files = (
        "rq1_contrib__drivers.csv",
        "rq1_contrib__summary.csv",
        "rq1_contrib__top_by_metric.csv",
    )

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

    def _load_driver_df(self, bench_dr) -> pd.DataFrame:
        return pd.read_csv(Path(bench_dr) / "tables/rq1_contrib__drivers.csv")

    # -----------------------
    # Curves
    # -----------------------
    def _topk_curve(self, arr: np.ndarray) -> pd.DataFrame:
        """Top-k cumulative contribution curve (sorted desc)."""
        x = np.asarray(arr, dtype=np.float64)
        x = x[~np.isnan(x)]
        if x.size == 0:
            return pd.DataFrame({"x": [0.0], "y": [0.0]})

        x = np.sort(x)[::-1]
        tot = float(np.sum(x))
        if tot <= 0:
            return pd.DataFrame({"x": [0.0], "y": [0.0]})

        cum = np.cumsum(x)
        xs = np.arange(1, x.size + 1, dtype=np.float64) / float(x.size)
        ys = cum / tot
        return pd.DataFrame({"x": xs, "y": ys})

    def _cdf_curve(self, arr: np.ndarray) -> pd.DataFrame:
        """True CDF of values."""
        x = np.asarray(arr, dtype=np.float64)
        x = x[~np.isnan(x)]
        if x.size == 0:
            return pd.DataFrame({"x": [0.0], "y": [0.0]})
        x = np.sort(x)
        y = np.arange(1, x.size + 1, dtype=np.float64) / float(x.size)
        return pd.DataFrame({"x": x, "y": y})

    # -----------------------
    # Stats
    # -----------------------
    def _gini(self, arr: np.ndarray) -> float:
        x = np.asarray(arr, dtype=np.float64)
        x = x[~np.isnan(x)]
        if x.size == 0:
            return float("nan")

        mn = float(np.min(x))
        if mn < 0:
            x = x - mn

        s = float(np.sum(x))
        if s == 0:
            return 0.0

        x = np.sort(x)
        n = x.size
        i = np.arange(1, n + 1, dtype=np.float64)
        return float((2.0 * np.sum(i * x)) / (n * s) - (n + 1) / n)

    def _summarize_metric(self, v: np.ndarray) -> Dict[str, float]:
        """
        Keep zeros: pct_zero is a key RQ1 observation.
        Tail: pct_lt_5pct_of_max uses < 5% of best driver within the benchmark.
        """
        x = np.asarray(v, dtype=np.float64)
        x = x[~np.isnan(x)]
        n = int(x.size)

        if n == 0:
            return {
                "n": 0,
                "mean": np.nan,
                "std": np.nan,
                "cv": np.nan,
                "min": np.nan,
                "p25": np.nan,
                "median": np.nan,
                "p75": np.nan,
                "max": np.nan,
                "pct_zero": np.nan,
                "pct_lt_5pct_of_max": np.nan,
                "top10_share": np.nan,
                "top20_share": np.nan,
                "gini": np.nan,
            }

        mean = float(np.mean(x))
        std = float(np.std(x, ddof=1)) if n > 1 else 0.0
        if mean > 0:
            cv = float(std / mean)
        else:
            cv = float("inf") if std > 0 else 0.0

        xmin = float(np.min(x))
        xmax = float(np.max(x))
        p25, med, p75 = np.percentile(x, [25, 50, 75])

        pct_zero = float(np.mean(x <= 0.0) * 100.0)
        pct_lt_5pct_of_max = float(np.mean(x < 0.05 * xmax) * 100.0) if xmax > 0 else 100.0

        xs = np.sort(x)[::-1]
        tot = float(np.sum(xs))
        k10 = max(1, int(np.ceil(0.10 * n)))
        k20 = max(1, int(np.ceil(0.20 * n)))
        top10_share = float(np.sum(xs[:k10]) / tot) if tot > 0 else 0.0
        top20_share = float(np.sum(xs[:k20]) / tot) if tot > 0 else 0.0

        return {
            "n": n,
            "mean": mean,
            "std": std,
            "cv": cv,
            "min": xmin,
            "p25": float(p25),
            "median": float(med),
            "p75": float(p75),
            "max": xmax,
            "pct_zero": pct_zero,
            "pct_lt_5pct_of_max": pct_lt_5pct_of_max,
            "top10_share": top10_share,
            "top20_share": top20_share,
            "gini": self._gini(x),
        }

    # -----------------------
    # Main
    # -----------------------
    def run(self) -> None:
        benches = self.discover_tables()
        print(f"Discovered {len(benches)} benchmarks with tables for RQ1Present.")

        summary_rows: List[dict] = []
        topk_frames: List[pd.DataFrame] = []
        cdf_frames: List[pd.DataFrame] = []
        top_rows: List[dict] = []

        # RQ1 metrics (CFG only) + crashes
        # - block_own: CFG basic-block coverage/contribution
        # - bug_count: crash count
        # Optional future extensions: cfg_edge_own / edge_own if you add them.
        candidate_metrics = [
            ("block_own", ["block_own", "bb_own", "block_cov", "bb_cov"]),
            ("bug_count", ["bug_count", "crash_count", "bugs", "crashes"]),
            ("cfg_edge_own", ["cfg_edge_own", "edge_own", "edge_cov"]),  # optional if exists
        ]

        TOPN = 10
        for bench in self.benchs:
            _bench_key = Path(bench).name
            try:
                df = self._load_driver_df(bench)
            except FileNotFoundError:
                print(f"Warning: driver contribution file not found for bench {bench}, skipping.")
                continue

            # bench/exe from file if present, else fallback
            bench = str(df["bench"].iloc[0]) if "bench" in df.columns else getattr(bt, "bench_key", _bench_key)
            exe = str(df["exe"].iloc[0]) if "exe" in df.columns else getattr(bt, "exe", _bench_key)

            drv_id_col = "driver_id" if "driver_id" in df.columns else None
            drv_name_col = "driver_name" if "driver_name" in df.columns else None

            for metric_name, aliases in candidate_metrics:
                col = next((c for c in aliases if c in df.columns), None)
                if col is None:
                    continue

                vals = df[col].to_numpy(dtype=np.float64)

                stats = self._summarize_metric(vals)
                summary_rows.append(
                    {
                        "bench": bench,
                        "exe": exe,
                        "metric": metric_name,
                        "col": col,
                        **stats,
                    }
                )

                topk = self._topk_curve(vals)
                topk.insert(0, "metric", metric_name)
                topk.insert(0, "exe", exe)
                topk.insert(0, "bench", bench)
                topk_frames.append(topk)

                cdf = self._cdf_curve(vals)
                cdf.insert(0, "metric", metric_name)
                cdf.insert(0, "exe", exe)
                cdf.insert(0, "bench", bench)
                cdf_frames.append(cdf)

                # Top-N drivers for appendix (skip if no driver columns)
                cols = [c for c in (drv_id_col, drv_name_col, col) if c is not None]
                if cols:
                    sub = df[cols].copy().rename(columns={col: "value"})
                    sub["metric"] = metric_name
                    sub["bench"] = bench
                    sub["exe"] = exe

                    sort_cols = ["value"]
                    ascending = [False]
                    if drv_id_col is not None:
                        sort_cols.append(drv_id_col)
                        ascending.append(True)

                    sub = sub.sort_values(sort_cols, ascending=ascending).head(TOPN)

                    if drv_id_col is None:
                        sub["driver_id"] = np.nan
                    else:
                        sub = sub.rename(columns={drv_id_col: "driver_id"})
                    if drv_name_col is None:
                        sub["driver_name"] = np.nan
                    else:
                        sub = sub.rename(columns={drv_name_col: "driver_name"})

                    top_rows.extend(
                        sub[["metric", "bench", "exe", "driver_id", "driver_name", "value"]]
                        .to_dict(orient="records")
                    )

        print(f"Generated summary for {len(summary_rows)} bench-metric combinations.")
        summary_df = pd.DataFrame(summary_rows).sort_values(["bench", "exe", "metric"])
        topk_df = pd.concat(topk_frames, ignore_index=True) if topk_frames else pd.DataFrame()
        cdf_df = pd.concat(cdf_frames, ignore_index=True) if cdf_frames else pd.DataFrame()
        top_df = pd.DataFrame(top_rows)

        self._write_csv("rq1_present__summary.csv", summary_df)
        if not topk_df.empty:
            self._write_csv("rq1_present__topk_curve.csv", topk_df)
        if not cdf_df.empty:
            self._write_csv("rq1_present__cdf.csv", cdf_df)
        if not top_df.empty:
            self._write_csv("rq1_present__top_by_metric.csv", top_df)

        print(
            f"[RQ1Present] wrote: summary({len(summary_df)} rows), "
            f"topk({len(topk_df)} rows), cdf({len(cdf_df)} rows), top({len(top_df)} rows) "
            f"to {self._get_out_dir()}"
        )