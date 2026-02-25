from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .present import Present, BenchTables


class RQ1Present(Present):
    name = "rq1"
    required_files = (
        "rq1_contrib__drivers.csv",
        "rq1_contrib__summary.csv",
        "rq1_contrib__top_by_metric.csv",
    )

    def _guess_cols(self, df: pd.DataFrame):
        # Customize to your actual column names for stability
        cols = {c.lower(): c for c in df.columns}
        drv = cols.get("drv_id") or cols.get("driver_id") or cols.get("driver") or df.columns[0]
        fc  = cols.get("fcov") or cols.get("func_cov") or cols.get("functions") or None
        ec  = cols.get("ecov") or cols.get("edge_cov") or cols.get("edges") or None
        return drv, fc, ec

    def _cdf(self, arr: np.ndarray) -> pd.DataFrame:
        arr = np.asarray(arr, dtype=np.float64)
        arr = arr[~np.isnan(arr)]
        arr = arr[arr > 0]
        if arr.size == 0:
            return pd.DataFrame({"x": [0.0], "y": [0.0]})
        arr = np.sort(arr)[::-1]
        cum = np.cumsum(arr)
        x = np.arange(1, arr.size + 1) / arr.size
        y = cum / cum[-1]
        return pd.DataFrame({"x": x, "y": y})

    def run(self) -> None:
        benches = self.discover_tables()

        summary_rows: List[dict] = []
        cdf_data: Dict[str, pd.DataFrame] = {}

        for bkey, t in benches.items():
            if not self.validate_tables(t):
                continue

            df_sum = self.read_csv(t, "rq1_contrib__summary.csv")
            df_drv = self.read_csv(t, "rq1_contrib__drivers.csv")

            row = {"benchmark": bkey, "exe": t.exe}
            if len(df_sum) > 0:
                row.update(df_sum.iloc[0].to_dict())

            # derive top10_share from per-driver if not already present
            drv_col, fc_col, ec_col = self._guess_cols(df_drv)

            # choose main metric for RQ1 plots/tables: function coverage first
            cov_col = fc_col or ec_col
            if cov_col is not None:
                vals = np.asarray(df_drv[cov_col], dtype=np.float64)
                vals = vals[~np.isnan(vals)]
                vals = np.sort(vals)[::-1]
                if vals.size > 0 and vals.sum() > 0:
                    k = max(1, int(np.ceil(0.10 * vals.size)))
                    row.setdefault("top10_share", float(vals[:k].sum() / vals.sum()))
                    cdf_data[bkey] = self._cdf(vals)

            row.setdefault("n_drivers", int(len(df_drv)))
            summary_rows.append(row)

        if not summary_rows:
            raise RuntimeError("RQ1Present: no benchmarks with rq1 tables were found.")

        df_summary = pd.DataFrame(summary_rows)

        # ---------- (1) LaTeX summary table ----------
        # Pick columns that exist (avoid breaking when some benches miss fields)
        cols = ["benchmark", "n_drivers"]
        for c in ["total_fcov", "total_ecov", "top10_share", "crashes"]:
            if c in df_summary.columns:
                cols.append(c)

        headers = ["Benchmark", "\\#Drv"]
        for c in cols[2:]:
            if c == "top10_share":
                headers.append("Top-10\\% share")
            elif c == "total_fcov":
                headers.append("Cov$_f$")
            elif c == "total_ecov":
                headers.append("Cov$_e$")
            else:
                headers.append(c.replace("_", "\\_"))

        # sort by skew if available
        if "top10_share" in df_summary.columns:
            df_summary = df_summary.sort_values("top10_share", ascending=False)

        tex = self.to_booktabs(
            df=df_summary,
            columns=cols,
            headers=headers,
            caption="RQ1 summary: driver contribution skew under equal fuzzing budgets.",
            label="tab:rq1_summary",
            align="l" + "r" * (len(cols) - 1),
        )
        self.write_tex("rq1_summary.tex", tex)

        # ---------- (2) Representative CDF figure ----------
        rep = df_summary["benchmark"].head(3).tolist()

        plt.figure()
        for b in rep:
            if b not in cdf_data:
                continue
            d = cdf_data[b]
            plt.plot(d["x"], d["y"], label=b)
        plt.xlabel("Fraction of drivers")
        plt.ylabel("Fraction of total coverage")
        plt.legend(fontsize="small")
        plt.tight_layout()
        plt.savefig(self.fig_dir / "rq1_cdf.pdf", format="pdf")
        plt.close()
        