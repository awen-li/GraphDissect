from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .present import Present


def _disambiguate_exe_labels(pairs: List[Tuple[str, str]], label_mode: str = "exe") -> List[str]:
    """
    pairs: list of (bench, exe) in display order.
    Returns list of labels; if exe duplicates exist, uses bench/exe for duplicates.
    """
    if label_mode == "bench_exe":
        return [f"{b}/{e}" for (b, e) in pairs]

    # exe-only with disambiguation
    labels = [e for (_b, e) in pairs]
    idxs: Dict[str, List[int]] = {}
    for i, (_b, e) in enumerate(pairs):
        idxs.setdefault(e, []).append(i)
    for e, pos in idxs.items():
        if len(pos) > 1:
            for i in pos:
                b, ee = pairs[i]
                labels[i] = f"{b}/{ee}"
    return labels


@dataclass
class _RQ6Cfg:
    cold_eps: float = 0.05
    min_region_size: int = 5
    topk_cold_regions: int = 10
    topk_drivers_per_cold_region: int = 5


class RQ6Present(Present):
    """
    RQ6 (final-only): Region-level structural imbalance under multi-driver fuzzing.

    Input (per-executable tables emitted by RQ6RegionImbalance analyzer):
      - tables/rq6_region_imbalance__summary.csv
      - tables/rq6_region_imbalance__regions.csv
      - tables/rq6_region_imbalance__driver_region.csv
      - tables/rq6_region_imbalance__hubs.csv

    Output (paper-ready):
      1) rq6_present__imbalance_summary.csv
      2) rq6_present__top_cold_regions.csv
      3) rq6_present__cold_region_driver_alignment.csv
      4) rq6_fig__rc_union_boxplots.pdf
      5) rq6_fig__coldfrac_barh.pdf
    """

    name = "rq6"
    required_files = (
        "rq6_region_imbalance__summary.csv",
        "rq6_region_imbalance__regions.csv",
        "rq6_region_imbalance__driver_region.csv",
        "rq6_region_imbalance__hubs.csv",
    )

    exe_rename: Dict[str, str] = None

    def __post_init__(self):
        if self.exe_rename is None:
            self.exe_rename = {"unbound-checkconf": "checkconf"}

    # -----------------------------
    # main
    # -----------------------------
    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        cfg = _RQ6Cfg()

        df_sum = self._normalize_frames(self._load_concat("rq6_region_imbalance__summary.csv"))
        df_reg = self._normalize_frames(self._load_concat("rq6_region_imbalance__regions.csv"))
        df_dr  = self._normalize_frames(self._load_concat("rq6_region_imbalance__driver_region.csv"))
        df_hub = self._normalize_frames(self._load_concat("rq6_region_imbalance__hubs.csv"))

        # Sanity checks
        if not df_sum.empty:
            need = {"bench", "exe", "n_regions", "mean_rc", "gini_rc", "cold_frac", "cold_threshold_eps"}
            miss = sorted(need - set(df_sum.columns))
            if miss:
                raise KeyError(f"rq6_region_imbalance__summary.csv missing columns: {miss}")

        if not df_reg.empty:
            need = {"bench", "exe", "region", "region_size", "rc_union"}
            miss = sorted(need - set(df_reg.columns))
            if miss:
                raise KeyError(f"rq6_region_imbalance__regions.csv missing columns: {miss}")

        if not df_dr.empty:
            need = {"bench", "exe", "driver", "region", "rc_driver"}
            miss = sorted(need - set(df_dr.columns))
            if miss:
                raise KeyError(f"rq6_region_imbalance__driver_region.csv missing columns: {miss}")

        pair_order = self._build_bench_order()

        # Paper table 1: per-exe imbalance summary
        tab_summary = self.build_rq6_imbalance_summary_table(df_sum, cfg=cfg)
        if not tab_summary.empty:
            tab_summary = self._apply_pair_order(tab_summary, pair_order=pair_order)
        tab_summary.to_csv(out_dir / "rq6_present__imbalance_summary.csv", index=False)

        # Paper table 2: top cold regions per exe
        tab_cold = self.build_rq6_top_cold_regions_table(df_reg, cfg=cfg)
        if not tab_cold.empty:
            tab_cold = self._apply_pair_order(tab_cold, pair_order=pair_order, extra_sort=["rc_union", "region_size"])
        tab_cold.to_csv(out_dir / "rq6_present__top_cold_regions.csv", index=False)

        # Paper table 3: cold-region vs driver alignment + top drivers
        tab_align = self.build_rq6_cold_region_driver_alignment(df_reg, df_dr, cfg=cfg)
        if not tab_align.empty:
            tab_align = self._apply_pair_order(tab_align, pair_order=pair_order, extra_sort=["region", "rank"])
        tab_align.to_csv(out_dir / "rq6_present__cold_region_driver_alignment.csv", index=False)

        # Optional: keep suite-wide raw data for appendix/debug
        df_sum.to_csv(out_dir / "rq6_present__summary_raw.csv", index=False)
        df_reg.to_csv(out_dir / "rq6_present__regions_raw.csv", index=False)
        df_dr.to_csv(out_dir / "rq6_present__driver_region_raw.csv", index=False)
        df_hub.to_csv(out_dir / "rq6_present__hubs_raw.csv", index=False)

        # Paper appendix helper: SNDP hub stats (top degree hubs)
        tab_hubs = self.build_rq6_hubs_table(df_hub, topk=15)
        tab_hubs.to_csv(out_dir / "rq6_present__top_hubs.csv", index=False)

    def post_run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        cfg = _RQ6Cfg()

        df_reg = self._normalize_frames(self._load_concat("rq6_region_imbalance__regions.csv"))
        df_sum = self._normalize_frames(self._load_concat("rq6_region_imbalance__summary.csv"))

        self.plot_rq6_rc_union_boxplots(df_reg, out_dir, cfg=cfg)
        self.plot_rq6_coldfrac_barh(df_sum, out_dir, cfg=cfg)

        # merged two-panel figure
        self.plot_rq6_two_panel_imbalance(df_sum, df_reg, out_dir, cfg=cfg)

    # -----------------------------
    # ordering helpers
    # -----------------------------
    def _apply_pair_order(
        self,
        df: pd.DataFrame,
        pair_order: Dict[tuple[str, str], int],
        extra_sort: List[str] | None = None,
    ) -> pd.DataFrame:
        df = df.copy()
        df["_pair_ord"] = df.apply(lambda r: pair_order.get((r["bench"], r["exe"]), 10**9), axis=1)
        sort_cols = ["_pair_ord", "bench", "exe"]
        if extra_sort:
            sort_cols.extend(extra_sort)
        df = df.sort_values(sort_cols, kind="mergesort")
        return df.drop(columns=["_pair_ord"])

    def _exe_order_by_metric(self, df: pd.DataFrame, metric: str, ascending: bool = False) -> List[Tuple[str, str]]:
        if df is None or df.empty or metric not in df.columns:
            return []

        tmp = df[["bench", "exe", metric]].copy()
        tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])

        items: List[Tuple[Tuple[str, str], float]] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            vals = g[metric].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue
            items.append(((str(b), str(e)), float(np.median(vals))))

        items.sort(key=lambda t: (t[1], t[0][0], t[0][1]), reverse=not ascending)
        return [p for (p, _) in items]

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

        # numeric columns (summary)
        num_cols = [
            "n_whole_nodes", "n_whole_edges", "n_undirected_nodes", "n_undirected_edges",
            "sndp_degree_threshold", "sndp_mean", "sndp_std", "sndp_median", "sndp_mad",
            "sndp_q1", "sndp_q3", "sndp_iqr", "n_pruned_hubs", "pruned_hub_ratio",
            "n_regions", "region_size_entropy", "rc_entropy_proxy",
            "mean_rc", "var_rc", "gini_rc", "cold_threshold_eps", "cold_frac",
            "node", "deg_total",
            "region", "region_size", "covered_in_union", "rc_union",
            "covered_in_driver", "rc_driver",
        ]
        for c in num_cols:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")

        return out

    # -----------------------------
    # TABLES
    # -----------------------------
    def build_rq6_imbalance_summary_table(self, df_sum: pd.DataFrame, cfg: _RQ6Cfg) -> pd.DataFrame:
        if df_sum is None or df_sum.empty:
            return pd.DataFrame(columns=[
                "bench", "exe",
                "n_whole_nodes", "n_whole_edges",
                "n_pruned_hubs", "pruned_hub_ratio",
                "n_regions",
                "mean_rc", "var_rc", "gini_rc", "cold_frac",
            ])

        cols = [
            "bench", "exe",
            "n_whole_nodes", "n_whole_edges",
            "n_pruned_hubs", "pruned_hub_ratio",
            "n_regions",
            "mean_rc", "var_rc", "gini_rc",
            "cold_threshold_eps", "cold_frac",
        ]
        keep = [c for c in cols if c in df_sum.columns]
        out = df_sum[keep].copy()
        out["paper_min_region_size"] = cfg.min_region_size
        out["paper_cold_eps"] = cfg.cold_eps

        # rounding
        for c in ["pruned_hub_ratio", "mean_rc", "var_rc", "gini_rc", "cold_frac", "cold_threshold_eps", "paper_cold_eps"]:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce").round(3)

        return out

    def build_rq6_top_cold_regions_table(self, df_reg: pd.DataFrame, cfg: _RQ6Cfg) -> pd.DataFrame:
        if df_reg is None or df_reg.empty:
            return pd.DataFrame(columns=["bench", "exe", "region", "region_size", "covered_in_union", "rc_union"])

        tmp = df_reg.copy()
        tmp["region_size"] = pd.to_numeric(tmp.get("region_size"), errors="coerce")
        tmp["rc_union"] = pd.to_numeric(tmp.get("rc_union"), errors="coerce")
        tmp["covered_in_union"] = pd.to_numeric(tmp.get("covered_in_union"), errors="coerce")

        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["region_size", "rc_union"])
        tmp = tmp[tmp["region_size"].astype(int) >= cfg.min_region_size]
        tmp = tmp[tmp["rc_union"] <= cfg.cold_eps]

        if tmp.empty:
            return pd.DataFrame(columns=["bench", "exe", "region", "region_size", "covered_in_union", "rc_union"])

        rows: List[pd.DataFrame] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            gg = g.copy()
            gg["region"] = pd.to_numeric(gg.get("region"), errors="coerce")
            gg = gg.sort_values(["rc_union", "region_size"], ascending=[True, False], kind="mergesort")
            rows.append(gg.head(cfg.topk_cold_regions))

        out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
        keep = ["bench", "exe", "region", "region_size", "covered_in_union", "rc_union"]
        out = out[keep].copy()
        out["rc_union"] = out["rc_union"].round(3)
        return out

    def build_rq6_cold_region_driver_alignment(
        self,
        df_reg: pd.DataFrame,
        df_dr: pd.DataFrame,
        cfg: _RQ6Cfg,
    ) -> pd.DataFrame:
        """
        For each cold region, list the top drivers that touch it (by rc_driver).

        Output columns:
          bench, exe, region, region_size, rc_union,
          rank, driver, rc_driver, covered_in_driver
        """
        if df_reg is None or df_reg.empty:
            return pd.DataFrame(columns=[
                "bench","exe","region","region_size","rc_union",
                "rank","driver","rc_driver","covered_in_driver"
            ])

        reg = df_reg.copy()
        for c in ["region", "region_size", "rc_union"]:
            if c in reg.columns:
                reg[c] = pd.to_numeric(reg[c], errors="coerce")

        reg = reg.replace([np.inf, -np.inf], np.nan).dropna(subset=["region", "region_size", "rc_union"])
        reg = reg[reg["region_size"].astype(int) >= cfg.min_region_size]
        reg = reg[reg["rc_union"] <= cfg.cold_eps]
        if reg.empty:
            return pd.DataFrame(columns=[
                "bench","exe","region","region_size","rc_union",
                "rank","driver","rc_driver","covered_in_driver"
            ])

        # If driver table empty, return just region list
        if df_dr is None or df_dr.empty:
            out = reg[["bench", "exe", "region", "region_size", "rc_union"]].copy()
            out["rank"] = 1
            out["driver"] = ""
            out["rc_driver"] = 0.0
            out["covered_in_driver"] = 0
            out["rc_union"] = out["rc_union"].round(3)
            return out

        dr = df_dr.copy()
        for c in ["region", "rc_driver", "covered_in_driver"]:
            if c in dr.columns:
                dr[c] = pd.to_numeric(dr[c], errors="coerce")
        dr = dr.replace([np.inf, -np.inf], np.nan).dropna(subset=["region", "rc_driver"])

        # Keep only relevant (cold) regions by join
        key_cols = ["bench", "exe", "region"]
        cold_keys = reg[key_cols].drop_duplicates()
        dr2 = dr.merge(cold_keys, on=key_cols, how="inner")

        if dr2.empty:
            out = reg[["bench", "exe", "region", "region_size", "rc_union"]].copy()
            out["rank"] = 1
            out["driver"] = ""
            out["rc_driver"] = 0.0
            out["covered_in_driver"] = 0
            out["rc_union"] = out["rc_union"].round(3)
            return out

        # Top drivers per cold region
        rows: List[pd.DataFrame] = []
        for (b, e, r), g in dr2.groupby(["bench", "exe", "region"], sort=False):
            gg = g.copy()
            gg["rc_driver"] = pd.to_numeric(gg["rc_driver"], errors="coerce")
            gg = gg.replace([np.inf, -np.inf], np.nan).dropna(subset=["rc_driver"])
            gg = gg.sort_values(["rc_driver", "driver"], ascending=[False, True], kind="mergesort")
            gg = gg.head(cfg.topk_drivers_per_cold_region)

            gg = gg.assign(rank=np.arange(1, len(gg) + 1))
            # attach region size + union rc
            info = reg[(reg["bench"] == b) & (reg["exe"] == e) & (reg["region"] == r)][
                ["region_size", "rc_union"]
            ].head(1)
            if not info.empty:
                gg["region_size"] = float(info["region_size"].iloc[0])
                gg["rc_union"] = float(info["rc_union"].iloc[0])
            else:
                gg["region_size"] = np.nan
                gg["rc_union"] = np.nan

            rows.append(gg[[
                "bench","exe","region","region_size","rc_union",
                "rank","driver","rc_driver","covered_in_driver"
            ]])

        out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=[
            "bench","exe","region","region_size","rc_union",
            "rank","driver","rc_driver","covered_in_driver"
        ])

        for c in ["rc_union", "rc_driver"]:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce").round(3)
        if "region_size" in out.columns:
            out["region_size"] = pd.to_numeric(out["region_size"], errors="coerce").astype("Int64")
        if "covered_in_driver" in out.columns:
            out["covered_in_driver"] = pd.to_numeric(out["covered_in_driver"], errors="coerce").fillna(0).astype(int)

        return out

    def build_rq6_hubs_table(self, df_hub: pd.DataFrame, topk: int = 15) -> pd.DataFrame:
        if df_hub is None or df_hub.empty:
            return pd.DataFrame(columns=["bench", "exe", "node", "deg_total"])

        tmp = df_hub.copy()
        for c in ["node", "deg_total"]:
            if c in tmp.columns:
                tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["deg_total"])

        rows: List[pd.DataFrame] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            gg = g.sort_values(["deg_total", "node"], ascending=[False, True], kind="mergesort")
            rows.append(gg.head(topk))
        out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["bench", "exe", "node", "deg_total"])
        return out[["bench", "exe", "node", "deg_total"]].copy()

    # -----------------------------
    # FIGURES
    # -----------------------------
    def plot_rq6_rc_union_boxplots(self, df_reg: pd.DataFrame, out_dir: Path, cfg: _RQ6Cfg) -> Path:
        """
        Boxplot of RC_union distribution across regions per executable.
        Regions with size < MIN_REGION_SIZE are excluded.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rq6_fig__rc_union_boxplots.pdf"

        if df_reg is None or df_reg.empty:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: no data", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        tmp = df_reg[["bench", "exe", "region_size", "rc_union"]].copy()
        tmp["region_size"] = pd.to_numeric(tmp["region_size"], errors="coerce")
        tmp["rc_union"] = pd.to_numeric(tmp["rc_union"], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["region_size", "rc_union"])
        tmp = tmp[tmp["region_size"].astype(int) >= cfg.min_region_size]

        if tmp.empty:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, f"RQ6: no regions with |R| ≥ {cfg.min_region_size}", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        # Order executables by median rc_union ascending (more imbalanced first)
        exe_order = self._exe_order_by_metric(tmp, metric="rc_union", ascending=True)
        rank = {p: i for i, p in enumerate(exe_order)}

        groups: List[Tuple[str, str, str, np.ndarray]] = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            vals = g["rc_union"].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue
            groups.append((str(b), str(e), str(e), vals))

        groups.sort(key=lambda t: rank.get((t[0], t[1]), 10**9))

        labels = [t[2] for t in groups]
        data = [t[3] for t in groups]

        # Disambiguate duplicates in exe-only labels
        idxs_by_exe: Dict[str, List[int]] = {}
        for i, t in enumerate(groups):
            idxs_by_exe.setdefault(t[2], []).append(i)
        for exe_name, idxs in idxs_by_exe.items():
            if len(idxs) > 1:
                for i in idxs:
                    b, e, _, _ = groups[i]
                    labels[i] = f"{b}/{e}"

        n = max(len(labels), 1)
        fig_h = min(9.5, max(7.5, 0.22 * n))
        fig_w = 7.2
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))

        ax.boxplot(data, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        ax.set_title(f"RQ6: Region coverage distribution (|R|≥{cfg.min_region_size})", fontsize=10)
        ax.set_xlabel("RC(R)", fontsize=10)
        ax.set_xlim(0.0, 1.0)
        ax.axvline(cfg.cold_eps, linestyle="--", linewidth=1)
        ax.tick_params(axis="y", labelsize=10)
        ax.tick_params(axis="x", labelsize=10)

        fig.tight_layout()
        fig.savefig(out_path, dpi=600)
        plt.close(fig)
        return out_path

    def plot_rq6_coldfrac_barh(self, df_sum: pd.DataFrame, out_dir: Path, cfg: _RQ6Cfg) -> Path:
        """
        Horizontal bar chart of ColdFrac per executable.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rq6_fig__coldfrac_barh.pdf"

        if df_sum is None or df_sum.empty or "cold_frac" not in df_sum.columns:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: no data", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        tmp = df_sum[["bench", "exe", "cold_frac"]].copy()
        tmp["cold_frac"] = pd.to_numeric(tmp["cold_frac"], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["cold_frac"])
        if tmp.empty:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: no valid cold_frac values", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        tmp = tmp.sort_values(["cold_frac", "bench", "exe"], ascending=[False, True, True], kind="mergesort")

        # disambiguate exe duplicates
        seen: Dict[str, int] = {}
        labels: List[str] = []
        for _, r in tmp.iterrows():
            exe = str(r["exe"])
            bench = str(r["bench"])
            if exe not in seen:
                seen[exe] = 1
                labels.append(exe)
            else:
                labels.append(f"{bench}/{exe}")

        vals = tmp["cold_frac"].to_numpy(dtype=float)
        n = max(len(labels), 1)

        fig_h = min(9.5, max(6.5, 0.22 * n))
        fig_w = 7.2
        fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))

        y = np.arange(n)
        ax.barh(y, vals)
        ax.set_yticks(y, labels=labels)
        ax.invert_yaxis()
        ax.set_xlim(0.0, 1.0)
        ax.set_xlabel(f"ColdFrac (RC ≤ {cfg.cold_eps})", fontsize=10)
        ax.set_title("RQ6: Fraction of under-explored structural regions", fontsize=10)
        ax.tick_params(axis="y", labelsize=10)
        ax.tick_params(axis="x", labelsize=10)

        ax.axvline(0.5, linestyle="--", linewidth=1)
        fig.tight_layout()
        fig.savefig(out_path, dpi=600)
        plt.close(fig)
        return out_path
    
    def plot_rq6_two_panel_imbalance(
        self,
        df_sum: pd.DataFrame,
        df_reg: pd.DataFrame,
        out_dir: Path,
        cfg: _RQ6Cfg,
    ) -> Path:
        """
        Two-panel figure on one page:
          (a) ColdFrac per executable (barh)
          (b) RC_union distribution per executable (boxplot)
        Uses the SAME y-axis executable order for both panels.

        Output:
          rq6_fig__two_panel_imbalance.pdf
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rq6_fig__two_panel_imbalance.pdf"

        # -------------------------
        # Prepare summary (ColdFrac)
        # -------------------------
        if df_sum is None or df_sum.empty or "cold_frac" not in df_sum.columns:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: no data", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        sum_tmp = df_sum[["bench", "exe", "cold_frac"]].copy()
        sum_tmp["cold_frac"] = pd.to_numeric(sum_tmp["cold_frac"], errors="coerce")
        sum_tmp = sum_tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["cold_frac"])
        if sum_tmp.empty:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: no valid cold_frac values", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        # -------------------------
        # Prepare regions (RC_union)
        # -------------------------
        if df_reg is None or df_reg.empty or "rc_union" not in df_reg.columns:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(0.5, 0.5, "RQ6: regions missing", ha="center", va="center")
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        reg_tmp = df_reg[["bench", "exe", "region_size", "rc_union"]].copy()
        reg_tmp["region_size"] = pd.to_numeric(reg_tmp["region_size"], errors="coerce")
        reg_tmp["rc_union"] = pd.to_numeric(reg_tmp["rc_union"], errors="coerce")
        reg_tmp = reg_tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["region_size", "rc_union"])
        reg_tmp = reg_tmp[reg_tmp["region_size"].astype(int) >= cfg.min_region_size]

        # -------------------------
        # Common executable order
        # -------------------------
        # Use cold_frac DESC (most severe imbalance on top).
        sum_tmp = sum_tmp.sort_values(["cold_frac", "bench", "exe"], ascending=[False, True, True], kind="mergesort")
        exe_pairs: List[Tuple[str, str]] = [(str(b), str(e)) for b, e in zip(sum_tmp["bench"], sum_tmp["exe"])]

        labels = _disambiguate_exe_labels(exe_pairs, label_mode="exe")
        y = np.arange(len(labels))

        # ColdFrac aligned
        cold_vals = sum_tmp["cold_frac"].to_numpy(dtype=float)

        # RC_union boxplot data aligned (some exes may have no regions after filtering)
        box_data: List[np.ndarray] = []
        keep_pairs: List[Tuple[str, str]] = []
        keep_labels: List[str] = []
        keep_cold: List[float] = []

        reg_group = {(str(b), str(e)): g for (b, e), g in reg_tmp.groupby(["bench", "exe"], sort=False)}

        for (b, e), lab, cf in zip(exe_pairs, labels, cold_vals):
            g = reg_group.get((b, e))
            if g is None:
                # still keep it, but boxplot must have at least one value;
                # we skip exes with no region values from BOTH panels to keep axes aligned.
                continue
            vals = g["rc_union"].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size == 0:
                continue
            keep_pairs.append((b, e))
            keep_labels.append(lab)
            keep_cold.append(float(cf))
            box_data.append(vals)

        if len(keep_labels) == 0:
            fig, ax = plt.subplots(1, 1, figsize=(7.0, 3.0))
            ax.text(
                0.5,
                0.5,
                f"RQ6: no regions with |R|≥{cfg.min_region_size} for any executable",
                ha="center",
                va="center",
            )
            ax.axis("off")
            fig.tight_layout()
            fig.savefig(out_path, dpi=300)
            plt.close(fig)
            return out_path

        # rebuild y for kept only
        n = len(keep_labels)
        y = np.arange(n)
        cold_vals = np.array(keep_cold, dtype=float)

        # -------------------------
        # Plot: two panels
        # -------------------------
        fig_h = min(9.8, max(7.6, 0.22 * n))
        fig_w = 7.8
        fig, axes = plt.subplots(1, 2, figsize=(fig_w, fig_h), sharey=True)

        # (a) ColdFrac barh
        axes[0].barh(y, cold_vals, color="0.65", edgecolor="0.25", linewidth=0.6)
        axes[0].set_yticks(y, labels=keep_labels)
        axes[0].invert_yaxis()
        axes[0].set_xlim(0.0, 1.0)
        axes[0].set_xlabel(f"ColdFrac (RC ≤ {cfg.cold_eps})", fontsize=10)
        axes[0].set_title("(a) Cold-region fraction", fontsize=10)
        #axes[0].axvline(0.5, linestyle="--", linewidth=1)

        # (b) RC_union boxplots
        axes[1].boxplot(box_data, vert=False, labels=keep_labels, showfliers=False, whis=(5, 95))
        axes[1].set_xlim(0.0, 1.0)
        axes[1].set_xlabel("RC(R)", fontsize=10)
        axes[1].set_title(f"(b) Region coverage (|R|≥{cfg.min_region_size})", fontsize=10)
        axes[1].axvline(cfg.cold_eps, linestyle="--", linewidth=1)

        # Only left panel shows y labels
        axes[1].tick_params(axis="y", labelleft=False)

        for ax in axes:
            ax.tick_params(axis="y", labelsize=10)
            ax.tick_params(axis="x", labelsize=10)

        fig.tight_layout(w_pad=0.9)
        fig.savefig(out_path, dpi=600)
        plt.close(fig)
        return out_path
