from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .present import Present


class RQ3Present(Present):
    """
    RQ3 (final-only): Structural organization & modularity of driver-induced subgraphs.

    Input:
      - tables/rq3_driver_metrics.csv   (per-driver metrics emitted by RQ3 analyzer)

    Output (paper-ready tables):
      1) rq3_present__org_summary.csv
         Per (bench, exe) summary of organization / cohesion:
           - #Driver, #Nodes(backbone normalized is optional), median/dispersion of:
             n_nodes, n_edges, density, wcc_count, lcc_ratio, wcc_entropy,
             articulation_ratio, bridge_ratio

      2) rq3_present__mod_summary.csv
         Per (bench, exe) summary of modularity:
           - modularity_Q, community_count, largest_comm_ratio, community_entropy

      3) rq3_present__top_examples.csv
         Optional narrative examples: top-3 drivers per (bench, exe) for:
           - most cohesive (highest lcc_ratio)
           - most fragmented (highest wcc_count)
           - most modular (highest modularity_Q)
           - most glue-like (highest articulation_ratio)
    """

    name = "rq3"
    required_files = ("rq3_modularity__driver_metrics.csv",)

    # -----------------------------
    # Stats helpers
    # -----------------------------
    @staticmethod
    def _safe_stats(x: np.ndarray) -> dict:
        """
        Dispersion stats for a 1D array.
        """
        x = np.asarray(x, dtype=float)
        x = x[np.isfinite(x)]
        if x.size == 0:
            return dict(std=0.0, cv=0.0, min=0.0, median=0.0, max=0.0)

        mean = float(np.mean(x))  # only for CV
        std = float(np.std(x, ddof=0))
        cv = float(std / mean) if mean > 0 else 0.0
        return dict(
            std=std,
            cv=cv,
            min=float(np.min(x)),
            median=float(np.median(x)),
            max=float(np.max(x)),
        )

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

        df = self._load_concat("rq3_modularity__driver_metrics.csv")

        # Required columns from analyzer
        need = {
            "bench",
            "exe",
            "driver",
            "n_nodes",
            "n_edges",
            "density",
            "wcc_count",
            "lcc_ratio",
            "wcc_entropy",
            "modularity_Q",
            "community_count",
            "largest_comm_ratio",
            "community_entropy",
            "articulation_ratio",
            "bridge_ratio",
        }
        miss = sorted(need - set(df.columns))
        if miss:
            raise KeyError(f"rq3_driver_metrics.csv missing columns: {miss}")

        # Normalize / coerce numeric
        num_cols = sorted(list(need - {"bench", "exe", "driver"}))
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # Optional columns if present
        if "node_ratio" in df.columns:
            df["node_ratio"] = pd.to_numeric(df["node_ratio"], errors="coerce")
        if "edge_ratio" in df.columns:
            df["edge_ratio"] = pd.to_numeric(df["edge_ratio"], errors="coerce")

        key = ["bench", "exe"]
        pair_order = self._build_bench_order()

        org_rows = []
        mod_rows = []
        top_rows = []

        # Helper: extract top drivers per metric for narrative examples
        def add_topk(g: pd.DataFrame, metric: str, side: str, k: int = 3) -> None:
            gg = g[[*key, "driver", metric]].copy()
            gg = gg.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])
            if gg.empty:
                return
            gg = gg.sort_values(metric, ascending=(side == "low"), kind="mergesort").head(k)
            for rank, (_, row) in enumerate(gg.iterrows(), start=1):
                top_rows.append(
                    dict(
                        bench=row["bench"],
                        exe=row["exe"],
                        metric=metric,
                        side=("highest" if side == "high" else "lowest"),
                        rank=rank,
                        driver=row["driver"],
                        value=float(row[metric]),
                    )
                )

        for (bench, exe), g in df.groupby(key, sort=False):
            n_drv = int(g.shape[0])

            # -------------------------
            # Organization / cohesion
            # -------------------------
            # (Keep paper tables compact by focusing on representative metrics.)
            org_metrics = [
                ("n_nodes", "#Node"),
                ("n_edges", "#Edge"),
                ("density", "Density"),
                ("wcc_count", "#WCC"),
                ("lcc_ratio", "LCC"),
                ("wcc_entropy", "WCCEnt"),
                ("articulation_ratio", "Artic"),
                ("bridge_ratio", "Bridge"),
            ]

            # Optional: normalized footprint if you produced it
            if "node_ratio" in g.columns:
                org_metrics.insert(2, ("node_ratio", "NodeRatio"))
            if "edge_ratio" in g.columns:
                org_metrics.insert(3, ("edge_ratio", "EdgeRatio"))

            # Build one row per (bench, exe) with stats per metric
            row_org = {"bench": bench, "exe": exe, "#Driver": n_drv}
            # Also expose the executable-level medians of size for quick context
            row_org["MedianNodes"] = float(np.nanmedian(g["n_nodes"].to_numpy(dtype=float)))
            row_org["MedianEdges"] = float(np.nanmedian(g["n_edges"].to_numpy(dtype=float)))

            for col, alias in org_metrics:
                st = self._safe_stats(g[col].to_numpy(dtype=float))
                row_org[f"{alias}_Std"] = st["std"]
                row_org[f"{alias}_CV"] = st["cv"]
                row_org[f"{alias}_Min"] = st["min"]
                row_org[f"{alias}_Median"] = st["median"]
                row_org[f"{alias}_Max"] = st["max"]

            org_rows.append(row_org)

            # -------------------------
            # Modularity / communities
            # -------------------------
            mod_metrics = [
                ("modularity_Q", "Q"),
                ("community_count", "#Comm"),
                ("largest_comm_ratio", "LComm"),
                ("community_entropy", "CommEnt"),
            ]

            row_mod = {"bench": bench, "exe": exe, "#Driver": n_drv}
            for col, alias in mod_metrics:
                st = self._safe_stats(g[col].to_numpy(dtype=float))
                row_mod[f"{alias}_Std"] = st["std"]
                row_mod[f"{alias}_CV"] = st["cv"]
                row_mod[f"{alias}_Min"] = st["min"]
                row_mod[f"{alias}_Median"] = st["median"]
                row_mod[f"{alias}_Max"] = st["max"]

            mod_rows.append(row_mod)

            # -------------------------
            # Optional narrative examples (top-3 drivers)
            # -------------------------
            add_topk(g, "lcc_ratio", side="high", k=3)            # most cohesive
            add_topk(g, "wcc_count", side="high", k=3)            # most fragmented
            add_topk(g, "modularity_Q", side="high", k=3)         # most modular
            add_topk(g, "articulation_ratio", side="high", k=3)   # glue-like

        out_org = self._apply_pair_order(pd.DataFrame(org_rows), pair_order=pair_order)
        out_mod = self._apply_pair_order(pd.DataFrame(mod_rows), pair_order=pair_order)
        out_top = pd.DataFrame(top_rows)
        if not out_top.empty:
            out_top = self._apply_pair_order(out_top, pair_order, extra_sort=["metric", "side", "rank"])

        out_org.to_csv(out_dir / "rq3_present__org_summary.csv", index=False)
        out_mod.to_csv(out_dir / "rq3_present__mod_summary.csv", index=False)
        out_top.to_csv(out_dir / "rq3_present__top_examples.csv", index=False)

    def post_run(self):
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df = self._load_concat("rq3_modularity__driver_metrics.csv")

        # Create the three figures
        self.plot_rq3_lcc_boxplot(df, out_dir)
        self.plot_rq3_wcc_boxplot(df, out_dir)
        self.plot_rq3_modularity_boxplot(df, out_dir)

        # Create three figures together
        self.plot_rq3_three_panel_boxplots(df, out_dir)

    # -----------------------------
    # Data prep: per-executable distributions
    # -----------------------------
    @staticmethod
    def _prep_boxplot_groups(
        df: pd.DataFrame,
        metric: str,
        key: Tuple[str, str] = ("bench", "exe"),
        min_drivers: int = 2,
        drop_zeros: bool = False,
        label_mode: str = "exe",  # "exe" or "bench_exe"
        pair_order: list[tuple[str, str]] | None = None
    ) -> Tuple[List[str], List[np.ndarray]]:
        """
        Returns (labels, data_arrays) where each element in data_arrays is the per-driver
        distribution for one (bench, exe). Labels are sorted by median(metric).
        """
        if metric not in df.columns:
            raise KeyError(f"Missing metric column '{metric}' in input CSV")

        need = {key[0], key[1], metric}
        miss = sorted(need - set(df.columns))
        if miss:
            raise KeyError(f"Input CSV missing columns required for plot: {miss}")

        tmp = df[[key[0], key[1], metric]].copy()
        tmp[metric] = pd.to_numeric(tmp[metric], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=[metric])

        groups = []
        for (b, e), g in tmp.groupby(list(key), sort=False):
            vals = g[metric].to_numpy(dtype=float)
            if drop_zeros:
                vals = vals[vals != 0.0]
            vals = vals[np.isfinite(vals)]
            if vals.size < min_drivers:
                continue
            groups.append((b, e, vals, float(np.median(vals))))

        # sort executables by median(metric) for readability
        if pair_order is None:
            groups.sort(key=lambda t: t[3])
        else:
            rank = {pair: i for i, pair in enumerate(pair_order)}
            groups.sort(key=lambda t: rank.get((t[0], t[1]), 10**9))

        # label selection: exe-only by default (paper-friendly)
        if label_mode == "bench_exe":
            labels = [f"{b}/{e}" for (b, e, _, _) in groups]
        else:
            labels = [str(e) for (b, e, _, _) in groups]
            # disambiguate duplicates: if exe names repeat, switch those to bench/exe
            seen = {}
            for i, (b, e, _, _) in enumerate(groups):
                seen.setdefault(str(e), []).append(i)
            for exe_name, idxs in seen.items():
                if len(idxs) > 1:
                    for i in idxs:
                        b, e, _, _ = groups[i]
                        labels[i] = f"{b}/{e}"

        data = [vals for (_, _, vals, _) in groups]
        return labels, data


    # -----------------------------
    # Plotting: horizontal boxplot for paper
    # -----------------------------
    @staticmethod
    def _save_boxplot(
        labels: List[str],
        data: List[np.ndarray],
        out_path: Path,
        xlabel: str,
        title: str,
        *,
        horizontal: bool = True,            # True = paper-friendly
        showfliers: bool = False,            # keep stable
        whis: tuple[int, int] | float = (5, 95),
        ref_lines: Optional[List[float]] = None,  # e.g., [0.9]
        xlim: Optional[Tuple[float, float]] = None,
    ) -> None:
        """
        Single-figure boxplot (matplotlib only, no explicit colors).
        Default is horizontal for better readability with many executables.
        """
        out_path.parent.mkdir(parents=True, exist_ok=True)

        n = max(len(labels), 1)

        if horizontal:
            # Height scales with number of executables; bounded for paper
            fig_h = min(12.0, max(4.0, 0.28 * n))
            fig_w = 7.5  # good for single-column; increase to ~9 for two-column
            plt.figure(figsize=(fig_w, fig_h))
            plt.boxplot(
                data,
                vert=False,
                labels=labels,
                showfliers=showfliers,
                whis=whis,
            )
            plt.xlabel(xlabel)
            plt.title(title)

            if ref_lines:
                for v in ref_lines:
                    plt.axvline(v, linestyle="--", linewidth=1)

            if xlim:
                plt.xlim(*xlim)

            plt.tight_layout()
            plt.savefig(out_path, dpi=300)
            plt.close()
            return

        # fallback: vertical
        fig_w = min(24, max(10, 0.35 * n))
        fig_h = 5.0
        plt.figure(figsize=(fig_w, fig_h))
        plt.boxplot(data, showfliers=showfliers, whis=whis)
        plt.ylabel(xlabel)
        plt.title(title)

        plt.xticks(ticks=np.arange(1, n + 1), labels=labels, rotation=60, ha="right")
        if ref_lines:
            for v in ref_lines:
                plt.axhline(v, linestyle="--", linewidth=1)

        if xlim:
            plt.ylim(*xlim)

        plt.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close()


    # -----------------------------
    # Figure 1: Cohesion (LCC ratio)
    # -----------------------------
    def plot_rq3_lcc_boxplot(self, df: pd.DataFrame, out_dir: Path) -> Path:
        labels, data = self._prep_boxplot_groups(
            df,
            metric="lcc_ratio",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",  # compact labels; auto-disambiguates
        )
        out_path = out_dir / "rq3_fig__lcc_ratio_boxplot.pdf"
        self._save_boxplot(
            labels=labels,
            data=data,
            out_path=out_path,
            xlabel="LCC ratio (largest connected component / subgraph nodes)",
            title="RQ3: Cohesion across drivers (per executable)",
            horizontal=True,
            showfliers=False,
            whis=(5, 95),
            ref_lines=[0.9],           # cohesive threshold guide
            xlim=(0.0, 1.0),           # LCC is a ratio
        )
        return out_path


    # -----------------------------
    # Figure 2: Fragmentation (WCC count)
    # -----------------------------
    def plot_rq3_wcc_boxplot(self, df: pd.DataFrame, out_dir: Path) -> Path:
        labels, data = self._prep_boxplot_groups(
            df,
            metric="wcc_count",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",
        )
        out_path = out_dir / "rq3_fig__wcc_count_boxplot.pdf"
        self._save_boxplot(
            labels=labels,
            data=data,
            out_path=out_path,
            xlabel="#WCC (weakly connected components)",
            title="RQ3: Fragmentation across drivers (per executable)",
            horizontal=True,
            showfliers=False,
            whis=(5, 95),
            ref_lines=None,
            xlim=None,  # let matplotlib scale it
        )
        return out_path


    # -----------------------------
    # Figure 3: Modularity (Q)
    # -----------------------------
    def plot_rq3_modularity_boxplot(self, df: pd.DataFrame, out_dir: Path) -> Path:
        labels, data = self._prep_boxplot_groups(
            df,
            metric="modularity_Q",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",
        )
        out_path = out_dir / "rq3_fig__modularity_Q_boxplot.pdf"
        self._save_boxplot(
            labels=labels,
            data=data,
            out_path=out_path,
            xlabel="Modularity Q",
            title="RQ3: Modularity across drivers (per executable)",
            horizontal=True,
            showfliers=False,
            whis=(5, 95),
            ref_lines=[0.3],  # optional guide; remove if you dislike “magic” numbers
            xlim=(0.0, 1.0),  # Q usually in [0,1] under typical definitions
        )
        return out_path

    
    # -----------------------------
    # 3 Figures together
    # -----------------------------
    def plot_rq3_three_panel_boxplots(self, df: pd.DataFrame, out_dir: Path) -> Path:
        """
        One-page, 3 side-by-side horizontal boxplots (1 row x 3 cols):
        (a) LCC ratio
        (b) WCC count
        (c) Modularity Q
        All panels share the same executable order (sorted by median LCC).
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "rq3_fig__three_panel_boxplots.pdf"

        # ---- 1) Build a stable executable order by median LCC ----
        lcc_labels, lcc_data = self._prep_boxplot_groups(
            df,
            metric="lcc_ratio",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",
        )

        # Build explicit (bench, exe) order based on median LCC
        tmp = df[["bench", "exe", "lcc_ratio"]].copy()
        tmp["lcc_ratio"] = pd.to_numeric(tmp["lcc_ratio"], errors="coerce")
        tmp = tmp.replace([np.inf, -np.inf], np.nan).dropna(subset=["lcc_ratio"])

        pairs = []
        for (b, e), g in tmp.groupby(["bench", "exe"], sort=False):
            vals = g["lcc_ratio"].to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size < 2:
                continue
            pairs.append(((b, e), float(np.median(vals))))
        pairs.sort(key=lambda t: t[1])
        pair_order = [p for (p, _) in pairs]

        # ---- 2) Get WCC/Q data in the SAME order ----
        wcc_labels, wcc_data = self._prep_boxplot_groups(
            df,
            metric="wcc_count",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",
            pair_order=pair_order,
        )
        q_labels, q_data = self._prep_boxplot_groups(
            df,
            metric="modularity_Q",
            min_drivers=2,
            drop_zeros=False,
            label_mode="exe",
            pair_order=pair_order,
        )

        # Sanity: align labels (prefer LCC order)
        labels = lcc_labels
        if wcc_labels != labels or q_labels != labels:
            labels = lcc_labels
        labels = ["checkconf" if x == "unbound-checkconf" else x for x in labels]

        n = max(len(labels), 1)

        # 1 row x 3 columns: make it wider, height depends on #executables
        fig_h = min(10.5, max(7.5, 0.22 * n))
        fig_w = 9
        fig, axes = plt.subplots(1, 3, figsize=(fig_w, fig_h), sharey=True)

        # ---- Panel (a): LCC ----
        axes[0].boxplot(lcc_data, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        axes[0].axvline(0.9, linestyle="--", linewidth=1)
        axes[0].set_xlim(0.0, 1.0)
        axes[0].set_title("(a) Cohesion (LCC ratio)", fontsize=10)
        axes[0].set_xlabel("LCC ratio", fontsize=10)

        # ---- Panel (b): WCC ----
        axes[1].boxplot(wcc_data, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        axes[1].set_title("(b) Fragmentation (#WCC)", fontsize=10)
        axes[1].set_xlabel("#WCC", fontsize=10)

        # ---- Panel (c): Modularity Q ----
        axes[2].boxplot(q_data, vert=False, labels=labels, showfliers=False, whis=(5, 95))
        axes[2].axvline(0.3, linestyle="--", linewidth=1)
        axes[2].set_xlim(0.0, 1.0)
        axes[2].set_title("(c) Modularity (Q)", fontsize=10)
        axes[2].set_xlabel("Modularity Q", fontsize=10)

        # ---- Readability tweaks ----
        # Keep y labels only on the left-most panel
        axes[1].tick_params(axis="y", labelleft=False)
        axes[2].tick_params(axis="y", labelleft=False)

        for ax in axes:
            ax.tick_params(axis="y", labelsize=10)
            ax.tick_params(axis="x", labelsize=10)

        fig.tight_layout()
        fig.savefig(out_path, dpi=600)
        plt.close(fig)
        return out_path