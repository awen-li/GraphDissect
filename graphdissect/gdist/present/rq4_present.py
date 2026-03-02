from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .present import Present


class RQ4Present(Present):
    """
    RQ4 (final-only): Driver overlap and redundancy among driver-induced subgraphs.

    Input (per-executable tables emitted by RQ4 analyzer):
      - tables/rq4__pairs_iou.csv
      - tables/rq4__iou_distribution.csv
      - tables/rq4__top_overlapping_pairs_v.csv
      - tables/rq4__top_overlapping_pairs_e.csv

    Output (paper-ready):
      1) rq4_present__overlap_summary.csv
      2) rq4_present__top_pairs.csv
      3) rq4_fig__two_panel_iou_boxplots.pdf
    """

    name = "rq4"
    required_files = (
        "rq4__pairs_iou.csv",
        "rq4__iou_distribution.csv",
        "rq4__top_overlapping_pairs_v.csv",
        "rq4__top_overlapping_pairs_e.csv",
    )

    exe_rename: Dict[str, str] = None

    def __post_init__(self):
        if self.exe_rename is None:
            self.exe_rename = {"unbound-checkconf": "checkconf"}

    def _apply_pair_order(
        self,
        df: pd.DataFrame,
        pair_order: Dict[tuple[str, str], int],
        extra_sort: List[str] | None = None,
    ) -> pd.DataFrame:
        df = df.copy()
        df["_pair_ord"] = df.apply(
            lambda r: pair_order.get((r["bench"], r["exe"]), 10**9),
            axis=1,
        )
        sort_cols = ["_pair_ord", "bench", "exe"]
        if extra_sort:
            sort_cols.extend(extra_sort)
        df = df.sort_values(sort_cols, kind="mergesort")
        return df.drop(columns=["_pair_ord"])

    # -----------------------------
    # main
    # -----------------------------
    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df_pairs = self._normalize_frames(self._load_concat("rq4__pairs_iou.csv"))
        df_dist  = self._normalize_frames(self._load_concat("rq4__iou_distribution.csv"))
        df_top_v = self._normalize_frames(self._load_concat("rq4__top_overlapping_pairs_v.csv"))
        df_top_e = self._normalize_frames(self._load_concat("rq4__top_overlapping_pairs_e.csv"))

        # Sanity: required columns (pairs)
        if not df_pairs.empty:
            need_pairs = {"bench", "exe", "iou_v", "iou_e"}
            miss = sorted(need_pairs - set(df_pairs.columns))
            if miss:
                raise KeyError(f"rq4__pairs_iou.csv missing columns: {miss}")

        # Sanity: required columns (dist)
        if not df_dist.empty:
            need_dist = {"bench", "exe", "num_pairs"}
            miss = sorted(need_dist - set(df_dist.columns))
            if miss:
                raise KeyError(f"rq4__iou_distribution.csv missing columns: {miss}")

        pair_order = self._build_bench_order()

        # Paper table 1: per-exe overlap summary
        tab_summary = self.build_rq4_overlap_summary_table(df_dist)
        if not tab_summary.empty:
            tab_summary = self._apply_pair_order(tab_summary, pair_order=pair_order)
        tab_summary.to_csv(out_dir / "rq4_present__overlap_summary.csv", index=False)

        # Paper table 2: top overlapping pairs (V/E)
        tab_top = self.build_rq4_top_pairs_table(df_top_v, df_top_e, k=5)
        if not tab_top.empty:
            tab_top = self._apply_pair_order(tab_top, pair_order=pair_order, extra_sort=["kind"])
        tab_top.to_csv(out_dir / "rq4_present__top_pairs.csv", index=False)

        # Optional: store suite-wide raw tables for debugging/appendix
        df_pairs.to_csv(out_dir / "rq4_present__pairs_iou.csv", index=False)
        df_dist.to_csv(out_dir / "rq4_present__iou_distribution.csv", index=False)

    def post_run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df_pairs = self._normalize_frames(self._load_concat("rq4__pairs_iou.csv"))
        self.plot_rq4_two_panel_iou_boxplots(df_pairs, out_dir)

    # -----------------------------
    # Normalize
    # -----------------------------
    def _normalize_frames(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()

        # ---- robust default (do NOT rely on __post_init__) ----
        exe_rename = self.exe_rename or {"unbound-checkconf": "checkconf"}

        if "bench" in out.columns:
            out["bench"] = out["bench"].astype(str)

        if "exe" in out.columns:
            out["exe"] = out["exe"].astype(str).map(lambda s: exe_rename.get(s, s))

        # numeric IoU columns
        for c in ("iou_v", "iou_e"):
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")

        # distribution/share columns
        for c in list(out.columns):
            if c == "num_pairs" or c.startswith("iou_") or c.startswith("share_iou_"):
                out[c] = pd.to_numeric(out[c], errors="coerce")

        # top-pair columns (optional)
        for c in ["driver_i", "driver_j", "size_i", "size_j", "inter", "union"]:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")

        return out

    # -----------------------------
    # FIGURE: two-column boxplots on one page
    # -----------------------------
    def plot_rq4_two_panel_iou_boxplots(self, df_pairs: pd.DataFrame, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rq4_fig__two_panel_iou_boxplots.pdf"

        if df_pairs is None or df_pairs.empty:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ4: no data", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        exe_order = self._exe_order_by_median(df_pairs, metric="iou_v")

        labels, data_v = self._prep_boxplot_groups_pairs(df_pairs, metric="iou_v", exe_order=exe_order)
        _,      data_e = self._prep_boxplot_groups_pairs(df_pairs, metric="iou_e", exe_order=exe_order)

        n = max(len(labels), 1)

        # narrow + tall: fit one page
        fig_h = min(9.5, max(7.5, 0.22 * n))
        fig_w = 7.6
        fig, axes = plt.subplots(1, 2, figsize=(fig_w, fig_h), sharey=True)

        axes[0].boxplot(data_v, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        axes[0].set_title("(a) Node overlap (IoU$_V$)", fontsize=10)
        axes[0].set_xlabel("IoU$_V$", fontsize=10)
        axes[0].set_xlim(0.0, 1.0)
        axes[0].axvline(0.5, linestyle="--", linewidth=1)

        axes[1].boxplot(data_e, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        axes[1].set_title("(b) Edge overlap (IoU$_E$)", fontsize=10)
        axes[1].set_xlabel("IoU$_E$", fontsize=10)
        axes[1].set_xlim(0.0, 1.0)
        axes[1].axvline(0.5, linestyle="--", linewidth=1)

        # only show y labels on left panel
        axes[1].tick_params(axis="y", labelleft=False)

        for ax in axes:
            ax.tick_params(axis="y", labelsize=10)
            ax.tick_params(axis="x", labelsize=10)

        fig.tight_layout(w_pad=0.8)
        fig.savefig(out_path, dpi=600)
        plt.close(fig)
        return out_path

    def _exe_order_by_median(self, df_pairs: pd.DataFrame, metric: str) -> List[Tuple[str, str]]:
        tmp = df_pairs[["bench", "exe", metric]].copy()
        tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])

        items: List[Tuple[Tuple[str, str], float]] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            vals = g[metric].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue
            items.append(((str(b), str(e)), float(np.median(vals))))

        # tie-breaker ensures stable ordering when medians match
        items.sort(key=lambda t: (t[1], t[0][0], t[0][1]))
        return [p for (p, _) in items]

    def _prep_boxplot_groups_pairs(
        self,
        df_pairs: pd.DataFrame,
        metric: str,
        exe_order: List[Tuple[str, str]],
        min_pairs: int = 1,
        label_mode: str = "exe",
    ) -> Tuple[List[str], List[np.ndarray]]:
        rank = {pair: i for i, pair in enumerate(exe_order)}

        tmp = df_pairs[["bench", "exe", metric]].copy()
        tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])

        groups: List[Tuple[str, str, str, float, np.ndarray]] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            vals = g[metric].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size < min_pairs:
                continue

            if label_mode == "bench_exe":
                label = f"{b}/{e}"
            else:
                label = str(e)

            groups.append((str(b), str(e), label, float(np.median(vals)), vals))

        groups.sort(key=lambda t: rank.get((t[0], t[1]), 10**9))

        labels = [t[2] for t in groups]
        data = [t[4] for t in groups]

        # disambiguate duplicates in exe-only mode (based on actual (bench,exe))
        if label_mode == "exe":
            idxs_by_exe: Dict[str, List[int]] = {}
            for i, t in enumerate(groups):
                idxs_by_exe.setdefault(t[2], []).append(i)
            for exe_name, idxs in idxs_by_exe.items():
                if len(idxs) > 1:
                    for i in idxs:
                        b, e, _, _, _ = groups[i]
                        labels[i] = f"{b}/{e}"

        return labels, data

    # -----------------------------
    # TABLES
    # -----------------------------
    def build_rq4_overlap_summary_table(self, df_dist: pd.DataFrame) -> pd.DataFrame:
        if df_dist is None or df_dist.empty:
            return pd.DataFrame(columns=[
                "bench", "exe", "num_pairs",
                "iou_v_median", "iou_v_p90", "share_iou_v_ge_0_5", "share_iou_v_ge_0_8",
                "iou_e_median", "iou_e_p90", "share_iou_e_ge_0_5", "share_iou_e_ge_0_8",
            ])

        cols = [
            "bench", "exe", "num_pairs",
            "iou_v_median", "iou_v_p90", "share_iou_v_ge_0_5", "share_iou_v_ge_0_8",
            "iou_e_median", "iou_e_p90", "share_iou_e_ge_0_5", "share_iou_e_ge_0_8",
        ]
        keep = [c for c in cols if c in df_dist.columns]
        out = df_dist[keep].copy()

        for c in out.columns:
            if c.startswith("iou_") or c.startswith("share_"):
                out[c] = pd.to_numeric(out[c], errors="coerce").round(3)

        return out

    def build_rq4_top_pairs_table(self, df_top_v: pd.DataFrame, df_top_e: pd.DataFrame, k: int = 5) -> pd.DataFrame:
        rows: List[pd.DataFrame] = []

        def _trim(df: pd.DataFrame, kind: str) -> pd.DataFrame:
            if df is None or df.empty:
                return pd.DataFrame(columns=[
                    "kind", "bench", "exe", "driver_i", "driver_j", "name_i", "name_j", "iou_v", "iou_e"
                ])

            keep = [c for c in ["bench","exe","driver_i","driver_j","name_i","name_j","iou_v","iou_e"] if c in df.columns]
            out = df[keep].copy()
            out.insert(0, "kind", kind)

            for c in ["iou_v", "iou_e"]:
                if c in out.columns:
                    out[c] = pd.to_numeric(out[c], errors="coerce")

            # sort inside each kind by the corresponding IoU if available
            sort_col = "iou_v" if kind == "top_by_iou_v" else "iou_e"
            if sort_col in out.columns:
                out = out.sort_values(sort_col, ascending=False, kind="mergesort")

            for c in ["iou_v", "iou_e"]:
                if c in out.columns:
                    out[c] = out[c].round(3)

            return out.head(k)

        rows.append(_trim(df_top_v, "top_by_iou_v"))
        rows.append(_trim(df_top_e, "top_by_iou_e"))

        return pd.concat(rows, ignore_index=True)