from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .present import Present


class RQ2Present(Present):
    """
    RQ2 (final-only): Do drivers exhibit heterogeneous fuzzing effectiveness under equal time budgets?

    Input per benchmark directory:
      - tables/rq1_contrib__drivers.csv

    Required columns:
      bench, exe, driver_id, driver_name,
      cg_node_own, cd_edge_own, block_own, bug_count

    Outputs (written to presenter output dir):
      - rq2_present__summary.csv
      - rq2_present__topk_curve.csv
      - rq2_present__cdf.csv
      - rq2_present__top_by_metric.csv
    """

    name = "rq2"
    required_files = (
        "rq1_contrib__drivers.csv",
        "rq1_contrib__summary.csv",
        "rq1_contrib__top_by_metric.csv",
    )

    REQUIRED_COLS = [
        "bench",
        "exe",
        "driver_id",
        "driver_name",
        "cg_node_own",
        "cd_edge_own",
        "block_own",
        "bug_count",
    ]

    METRICS: List[Tuple[str, str]] = [
        ("cg_node_own", "cg_node_own"),
        ("cd_edge_own", "cd_edge_own"),
        ("block_own", "block_own"),
        ("bug_count", "bug_count"),
    ]

    TOPN = 10

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
                f"RQ2Present: missing required columns {missing} in "
                f"{Path(bench_dir) / 'tables/rq1_contrib__drivers.csv'}; "
                f"found columns={list(df.columns)}"
            )

    # -----------------------
    # Curves
    # -----------------------
    def _topk_curve(self, arr: np.ndarray) -> pd.DataFrame:
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
        cv = float(std / mean) if mean > 0 else (float("inf") if std > 0 else 0.0)

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
        print(f"RQ2Present: scanning {len(self.benchs)} benchmark dirs...")

        summary_rows: List[dict] = []
        topk_frames: List[pd.DataFrame] = []
        cdf_frames: List[pd.DataFrame] = []
        top_rows: List[dict] = []

        for bench_dir in self.benchs:
            df = self._load_driver_df(bench_dir)
            self._require_cols(df, bench_dir)

            bench_name = str(df["bench"].iloc[0])
            exe_name = str(df["exe"].iloc[0])

            for metric_name, col in self.METRICS:
                vals = df[col].to_numpy(dtype=np.float64)

                stats = self._summarize_metric(vals)
                summary_rows.append(
                    {
                        "bench": bench_name,
                        "exe": exe_name,
                        "metric": metric_name,
                        "col": col,
                        **stats,
                    }
                )

                topk = self._topk_curve(vals)
                topk.insert(0, "metric", metric_name)
                topk.insert(0, "exe", exe_name)
                topk.insert(0, "bench", bench_name)
                topk_frames.append(topk)

                cdf = self._cdf_curve(vals)
                cdf.insert(0, "metric", metric_name)
                cdf.insert(0, "exe", exe_name)
                cdf.insert(0, "bench", bench_name)
                cdf_frames.append(cdf)

                # Top-N drivers (appendix)
                sub = df[["driver_id", "driver_name", col]].copy().rename(columns={col: "value"})
                sub["metric"] = metric_name
                sub["bench"] = bench_name
                sub["exe"] = exe_name
                sub = sub.sort_values(["value", "driver_id"], ascending=[False, True]).head(self.TOPN)

                top_rows.extend(
                    sub[["metric", "bench", "exe", "driver_id", "driver_name", "value"]]
                    .to_dict(orient="records")
                )

        summary_df = pd.DataFrame(summary_rows).sort_values(["bench", "exe", "metric"])
        topk_df = pd.concat(topk_frames, ignore_index=True) if topk_frames else pd.DataFrame()
        cdf_df = pd.concat(cdf_frames, ignore_index=True) if cdf_frames else pd.DataFrame()
        top_df = pd.DataFrame(top_rows)

        self._write_csv("rq2_present__summary.csv", summary_df)
        self._write_csv("rq2_present__topk_curve.csv", topk_df)
        self._write_csv("rq2_present__cdf.csv", cdf_df)
        self._write_csv("rq2_present__top_by_metric.csv", top_df)

        print(
            f"[RQ2Present] wrote: summary({len(summary_df)} rows), "
            f"topk({len(topk_df)} rows), cdf({len(cdf_df)} rows), top({len(top_df)} rows) "
            f"to {self._get_out_dir()}"
        )