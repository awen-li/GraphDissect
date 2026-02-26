from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from .present import Present


class RQ2Present(Present):
    """
    RQ2 (final-only): Do different drivers exhibit heterogeneous effectiveness under equal time budgets?

    Effectiveness metrics:
      - cg_node_own  (function-level activation)
      - cd_edge_own  (dependence-edge activation)

    IMPORTANT:
      - Overlap exists, so executable-level totals MUST come from rq1_contrib__summary.csv:
          sum_cg_node_own, sum_cd_edge_own
      - We report heterogeneity primarily on normalized per-driver shares:
          cg_node_share = cg_node_own / sum_cg_node_own
          cd_edge_share = cd_edge_own / sum_cd_edge_own

    Inputs:
      - tables/rq1_contrib__drivers.csv
      - tables/rq1_contrib__summary.csv
      - tables/rq1_contrib__top_by_metric.csv (not used; kept only for pipeline compatibility)

    Outputs:
      - rq2_present__node_summary.csv
      - rq2_present__edge_summary.csv
      - rq2_present__top_by_metric.csv (optional examples: best/worst drivers by each metric)
    """

    name = "rq2"
    required_files = (
        "rq1_contrib__drivers.csv",
        "rq1_contrib__summary.csv",
        "rq1_contrib__top_by_metric.csv",  # not used; safe to remove if your CLI expects it
    )

    # -----------------------------
    # IO helpers
    # -----------------------------
    def _discover_tables(self, filename: str) -> List[Path]:
        suite_dir = Path(self.suite_dir)
        return sorted(suite_dir.glob(f"**/tables/{filename}"))

    def _load_concat(self, filename: str) -> pd.DataFrame:
        paths = self._discover_tables(filename)
        if not paths:
            raise FileNotFoundError(f"No inputs found for {filename} under {self.suite_dir}")
        return pd.concat((pd.read_csv(p) for p in paths), ignore_index=True)

    # -----------------------------
    # Data sanity helpers
    # -----------------------------
    @staticmethod
    def _dedup_summary(summ: pd.DataFrame) -> pd.DataFrame:
        key = ["bench", "exe"]
        required = ["sum_cg_node_own", "sum_cd_edge_own", "num_drivers"]
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
                f"{gshow.to_string(index=False)}\n"
                "Fix the input suite so each executable has exactly one consistent summary row."
            )

        return summ.drop_duplicates(subset=key, keep="first")

    @staticmethod
    def _safe_stats(x: np.ndarray) -> dict:
        """
        Minimal dispersion stats for a 1D array (normalized shares).
        """
        x = np.asarray(x, dtype=float)
        x = x[np.isfinite(x)]
        if x.size == 0:
            return dict(mean=0.0, std=0.0, cv=0.0, min=0.0, median=0.0, max=0.0)

        mean = float(np.mean(x))
        std = float(np.std(x, ddof=0))
        cv = float(std / mean) if mean > 0 else 0.0
        return dict(
            mean=mean,
            std=std,
            cv=cv,
            min=float(np.min(x)),
            median=float(np.median(x)),
            max=float(np.max(x)),
        )

    def _apply_pair_order(self, df: pd.DataFrame, 
                          pair_order: dict[tuple[str, str], int],
                          extra_sort: list[str] | None = None) -> pd.DataFrame:
        df = df.copy()
        df["_pair_ord"] = df.apply(
            lambda r: pair_order.get((r["bench"], r["exe"]), 10**9),
            axis=1,
        )
        sort_cols = ["_pair_ord", "bench", "exe"]
        if extra_sort:
            sort_cols.extend(extra_sort)
        # stable sort for deterministic outputs
        df = df.sort_values(sort_cols, kind="mergesort")
        return df.drop(columns=["_pair_ord"])

    # -----------------------------
    # main
    # -----------------------------
    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        drv = self._load_concat("rq1_contrib__drivers.csv")
        summ = self._load_concat("rq1_contrib__summary.csv")

        need_drv = {"bench", "exe", "driver_id", "driver_name", "cg_node_own", "cd_edge_own"}
        miss = sorted(need_drv - set(drv.columns))
        if miss:
            raise KeyError(f"rq1_contrib__drivers.csv missing columns: {miss}")

        summ = self._dedup_summary(summ)

        key = ["bench", "exe"]
        cols = key + ["num_drivers", "sum_cg_node_own", "sum_cd_edge_own", "exe_dir"]
        cols_present = [c for c in cols if c in summ.columns]
        summ2 = summ[cols_present].copy()

        # many-to-one merge is now safe
        df = drv.merge(summ2, on=key, how="left", validate="many_to_one")

        # overlap-aware totals from summary
        df["node_total"] = df["sum_cg_node_own"].astype(float)
        df["edge_total"] = df["sum_cd_edge_own"].astype(float)

        # normalized effectiveness shares (scale-free, comparable across exes)
        df["cg_node_share"] = np.where(df["node_total"] > 0, df["cg_node_own"] / df["node_total"], 0.0)
        df["cd_edge_share"] = np.where(df["edge_total"] > 0, df["cd_edge_own"] / df["edge_total"], 0.0)

        node_rows = []
        edge_rows = []
        top_rows = []

        for (bench, exe), g in df.groupby(key, sort=False):
            exe_dir = g["exe_dir"].iloc[0] if "exe_dir" in g.columns else ""
            n = (
                int(g["num_drivers"].iloc[0])
                if ("num_drivers" in g.columns and pd.notna(g["num_drivers"].iloc[0]))
                else int(g.shape[0])
            )

            node_share = g["cg_node_share"].to_numpy(dtype=float)
            edge_share = g["cd_edge_share"].to_numpy(dtype=float)

            ns = self._safe_stats(node_share)
            es = self._safe_stats(edge_share)

            node_rows.append(
                dict(
                    bench=bench,
                    exe=exe,
                    exe_dir=exe_dir,
                    num_drivers=n,
                    sum_cg_node_own=float(g["sum_cg_node_own"].iloc[0]),
                    mean_share=ns["mean"],
                    std_share=ns["std"],
                    cv_share=ns["cv"],
                    min_share=ns["min"],
                    median_share=ns["median"],
                    max_share=ns["max"],
                )
            )

            edge_rows.append(
                dict(
                    bench=bench,
                    exe=exe,
                    exe_dir=exe_dir,
                    num_drivers=n,
                    sum_cd_edge_own=float(g["sum_cd_edge_own"].iloc[0]),
                    mean_share=es["mean"],
                    std_share=es["std"],
                    cv_share=es["cv"],
                    min_share=es["min"],
                    median_share=es["median"],
                    max_share=es["max"],
                )
            )

            # Optional examples (best/worst) for narrative
            def add_extremes(metric_name: str, share_col: str, raw_col: str) -> None:
                gg = g[[*key, "driver_id", "driver_name", share_col, raw_col]].copy()
                gg = gg.replace([np.inf, -np.inf], np.nan).dropna(subset=[share_col])
                if gg.empty:
                    return

                best = gg.sort_values(share_col, ascending=False).head(3)
                worst = gg.sort_values(share_col, ascending=True).head(3)

                for rank, (_, row) in enumerate(best.iterrows(), start=1):
                    top_rows.append(
                        dict(
                            bench=bench,
                            exe=exe,
                            metric=metric_name,
                            side="best",
                            rank=rank,
                            driver_id=row["driver_id"],
                            driver_name=row.get("driver_name", ""),
                            value_raw=float(row[raw_col]),
                            value_share=float(row[share_col]),
                        )
                    )
                for rank, (_, row) in enumerate(worst.iterrows(), start=1):
                    top_rows.append(
                        dict(
                            bench=bench,
                            exe=exe,
                            metric=metric_name,
                            side="worst",
                            rank=rank,
                            driver_id=row["driver_id"],
                            driver_name=row.get("driver_name", ""),
                            value_raw=float(row[raw_col]),
                            value_share=float(row[share_col]),
                        )
                    )

            add_extremes("cg_node_own", "cg_node_share", "cg_node_own")
            add_extremes("cd_edge_own", "cd_edge_share", "cd_edge_own")

        pair_order = self._build_bench_order()

        out_node = self._apply_pair_order(pd.DataFrame(node_rows), pair_order=pair_order)
        out_edge = self._apply_pair_order(pd.DataFrame(edge_rows), pair_order=pair_order)
        out_top = pd.DataFrame(top_rows)
        if not out_top.empty:
            out_top = self._apply_pair_order(out_top, pair_order, extra_sort=["metric", "side", "rank"])

        out_node.to_csv(out_dir / "rq2_present__node_summary.csv", index=False)
        out_edge.to_csv(out_dir / "rq2_present__edge_summary.csv", index=False)
        out_top.to_csv(out_dir / "rq2_present__top_by_metric.csv", index=False)