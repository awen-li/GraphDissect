from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


# -----------------------------
# Small math helpers
# -----------------------------
def _safe_log(x: float) -> float:
    return math.log(x) if x > 0 else 0.0


def _entropy_from_sizes(sizes: List[int], normalize: bool = True) -> float:
    total = sum(sizes)
    if total <= 0:
        return 0.0
    probs = [s / total for s in sizes if s > 0]
    if not probs:
        return 0.0
    h = -sum(p * _safe_log(p) for p in probs)
    if not normalize:
        return h
    k = len(probs)
    return h / _safe_log(k) if k > 1 else 0.0


def _gini(values: List[float]) -> float:
    """
    Gini coefficient for non-negative values.
    Returns 0.0 for empty/all-zero.
    """
    xs = [max(0.0, float(v)) for v in values]
    n = len(xs)
    if n == 0:
        return 0.0
    s = sum(xs)
    if s <= 0:
        return 0.0
    xs.sort()
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    return (2.0 * cum) / (n * s) - (n + 1) / n


def _import_nx():
    try:
        import networkx as nx  # type: ignore
    except Exception as e:
        raise RuntimeError("RQ6RegionImbalance requires networkx (`pip install networkx`).") from e
    return nx

# -----------------------------
# Adaptive SNDP implementation
# -----------------------------
@dataclass
class SNDPStats:
    mode: str
    n: int
    mean: float
    std: float
    median: float
    mad: float
    q1: float
    q3: float
    iqr: float
    threshold: float
    pruned: int
    pruned_frac: float


def _percentile(sorted_x: List[float], p: float) -> float:
    """p in [0,1]. Linear interpolation."""
    if not sorted_x:
        return 0.0
    if p <= 0:
        return float(sorted_x[0])
    if p >= 1:
        return float(sorted_x[-1])
    n = len(sorted_x)
    pos = (n - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_x[lo])
    frac = pos - lo
    return float(sorted_x[lo] * (1 - frac) + sorted_x[hi] * frac)


def _median(sorted_x: List[float]) -> float:
    return _percentile(sorted_x, 0.5)


def _mad(sorted_x: List[float], med: float) -> float:
    dev = sorted([abs(x - med) for x in sorted_x])
    return _median(dev)


def _sndp_threshold_from_stats(x_sorted: List[float], mode: str, z: float, mad_k: float) -> float:
    """
    Returns degree threshold T; prune nodes with deg >= T.
    modes: zscore, mad, iqr, quantile, hybrid
    """
    n = len(x_sorted)
    if n == 0:
        return float("inf")

    mean = sum(x_sorted) / n
    var = sum((v - mean) ** 2 for v in x_sorted) / n
    std = math.sqrt(var)

    med = _median(x_sorted)
    mad = _mad(x_sorted, med)

    q1 = _percentile(x_sorted, 0.25)
    q3 = _percentile(x_sorted, 0.75)
    iqr = max(0.0, q3 - q1)

    p95 = _percentile(x_sorted, 0.95)
    p98 = _percentile(x_sorted, 0.98)

    mode = mode.lower().strip()
    if mode == "zscore":
        return (mean + z * std) if std > 1e-12 else p98
    if mode == "mad":
        return (med + mad_k * mad) if mad > 1e-12 else p98
    if mode == "iqr":
        return (q3 + mad_k * iqr) if iqr > 1e-12 else p98
    if mode == "quantile":
        # in this mode, z is treated as quantile in [0.5, 0.999]
        q = min(0.999, max(0.5, z))
        return _percentile(x_sorted, q)
    if mode == "hybrid":
        t1 = (mean + z * std) if std > 1e-12 else p95
        t2 = (med + mad_k * mad) if mad > 1e-12 else p95
        t3 = (q3 + mad_k * iqr) if iqr > 1e-12 else p95
        return max(t1, t2, t3, p95)
    return p98


def _sndp_prune_nodes(
    deg_total: Dict[int, int],
    mode: str = "hybrid",
    z: float = 2.5,
    mad_k: float = 6.0,
    min_prune: int = 1,
    max_prune_frac: float = 0.02,
) -> Tuple[Set[int], SNDPStats]:
    """
    Adaptive SNDP pruning over total-degree distribution.
    - Computes an adaptive threshold from distribution stats
    - Prunes nodes with deg >= threshold
    - Caps pruning by max_prune_frac
    - Ensures at least min_prune (if graph not tiny)
    """
    items = [(int(n), int(d)) for n, d in deg_total.items()]
    n = len(items)
    if n == 0:
        stats = SNDPStats(
            mode=mode, n=0, mean=0.0, std=0.0, median=0.0, mad=0.0,
            q1=0.0, q3=0.0, iqr=0.0, threshold=float("inf"),
            pruned=0, pruned_frac=0.0
        )
        return set(), stats

    degs = [float(d) for _node, d in items]
    degs_sorted = sorted(degs)

    mean = sum(degs_sorted) / n
    var = sum((v - mean) ** 2 for v in degs_sorted) / n
    std = math.sqrt(var)
    med = _median(degs_sorted)
    mad = _mad(degs_sorted, med)
    q1 = _percentile(degs_sorted, 0.25)
    q3 = _percentile(degs_sorted, 0.75)
    iqr = max(0.0, q3 - q1)

    thr = _sndp_threshold_from_stats(degs_sorted, mode=mode, z=z, mad_k=mad_k)
    hubs = {node for (node, d) in items if float(d) >= thr}

    # Deterministic trimming/expansion by degree rank.
    items_desc = sorted(items, key=lambda x: x[1], reverse=True)

    cap = int(max(1, math.floor(max_prune_frac * n))) if max_prune_frac > 0 else n
    cap = min(cap, n)

    if len(hubs) > cap:
        hubs = {node for (node, _d) in items_desc[:cap]}

    if n >= 10 and len(hubs) < min_prune:
        want = min(min_prune, cap)
        hubs = {node for (node, _d) in items_desc[:want]}

    stats = SNDPStats(
        mode=mode,
        n=n,
        mean=float(mean),
        std=float(std),
        median=float(med),
        mad=float(mad),
        q1=float(q1),
        q3=float(q3),
        iqr=float(iqr),
        threshold=float(thr),
        pruned=len(hubs),
        pruned_frac=(len(hubs) / n) if n else 0.0,
    )
    return hubs, stats


# -----------------------------
# Region / coverage helpers
# -----------------------------
def _build_whole_graph(nx, g):
    nodes, edges = g.get_whole_graph()
    G = nx.DiGraph()
    G.add_nodes_from(int(n) for n in nodes)
    G.add_edges_from((int(u), int(v)) for (u, v) in edges if int(u) != int(v))
    return G


def _community_detect_greedy(nx, Gu) -> List[Set[int]]:
    """
    Greedy modularity maximization communities; no extra deps.
    Returns list of node sets.
    """
    if Gu.number_of_nodes() == 0:
        return []
    if Gu.number_of_nodes() == 1:
        u = next(iter(Gu.nodes()))
        return [{int(u)}]
    if Gu.number_of_edges() == 0:
        return [{int(u)} for u in Gu.nodes()]

    from networkx.algorithms.community import greedy_modularity_communities

    comms = list(greedy_modularity_communities(Gu))
    return [set(int(x) for x in c) for c in comms] if comms else [{int(u)} for u in Gu.nodes()]


def _union_covered_nodes(g) -> Set[int]:
    u: Set[int] = set()
    for drv_id in g.drvList.keys():
        nodes, _edges = g.get_driver_graph(drv_id)
        u |= {int(x) for x in nodes}
    return u


# -----------------------------
# RQ6 Analyzer
# -----------------------------
class RQ6RegionImbalance(Analyzer):
    """
    Computes:
      - community-based structural regions on pruned whole-callgraph (SNDP)
      - region coverage under union multi-driver fuzzing
      - imbalance metrics: mean/var/Gini/cold fraction
      - driver-region alignment table (optional but useful for explanations)
    """
    key = "rq6_region_imbalance"
    description = "RQ6: Region-level imbalance under multi-driver fuzzing (SNDP + community regions)"

    # Default SNDP knobs (override in subclass or by setting fields)
    SNDP_MODE = "hybrid"          # zscore | mad | iqr | quantile | hybrid
    SNDP_Z = 2.5                  # z-score multiplier OR quantile (if mode=quantile)
    SNDP_MAD_K = 6.0              # robust multiplier for MAD/IQR/hybrid
    SNDP_MIN_PRUNE = 1            # guarantee at least this many hubs (if n>=10)
    SNDP_MAX_PRUNE_FRAC = 0.02    # cap hub pruning fraction
    MIN_REGION_SIZE = 5           # minimal region size

    # Cold region threshold
    COLD_EPS = 0.05

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        nx = _import_nx()
        g = ctx.ensure_drvgraph()

        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        # Whole graph (directed) + undirected projection for communities
        G = _build_whole_graph(nx, g)
        Gu = nx.Graph(G)  # undirected projection

        # --- SNDP pruning on total degree (in + out) ---
        deg_total: Dict[int, int] = {int(v): int(G.in_degree(v) + G.out_degree(v)) for v in G.nodes()}

        V_hub, sndp_stats = _sndp_prune_nodes(
            deg_total,
            mode=self.SNDP_MODE,
            z=self.SNDP_Z,
            mad_k=self.SNDP_MAD_K,
            min_prune=self.SNDP_MIN_PRUNE,
            max_prune_frac=self.SNDP_MAX_PRUNE_FRAC,
        )

        Gu_p = Gu.copy()
        if V_hub:
            Gu_p.remove_nodes_from(V_hub)

        # Structural regions via community detection
        all_regions = _community_detect_greedy(nx, Gu_p)
        regions = [
            R for R in all_regions
            if len(R) >= self.MIN_REGION_SIZE
        ]

        n_regions_total = len(all_regions)
        n_regions_kept  = len(regions)
        n_regions_filtered = n_regions_total - n_regions_kept

        # Union coverage set
        C_union = _union_covered_nodes(g)

        # Region-level RC and imbalance metrics
        region_rows: List[Dict[str, Any]] = []
        rc_values: List[float] = []
        region_sizes: List[int] = []

        for rid, R in enumerate(regions):
            size = len(R)
            cov = len(R & C_union) if size > 0 else 0
            rc = (cov / size) if size > 0 else 0.0

            region_sizes.append(size)
            rc_values.append(rc)

            region_rows.append(
                {
                    "bench": bench_name,
                    "exe": exe_name,
                    "region": rid,
                    "region_size": size,
                    "covered_in_union": cov,
                    "rc_union": rc,
                }
            )

        k = len(regions)
        mean_rc = sum(rc_values) / k if k > 0 else 0.0
        var_rc = (sum((x - mean_rc) ** 2 for x in rc_values) / k) if k > 0 else 0.0
        gini_rc = _gini(rc_values)
        cold_eps = float(self.COLD_EPS)
        cold_frac = (sum(1 for x in rc_values if x <= cold_eps) / k) if k > 0 else 0.0

        # Helpful summaries for reporting/debugging
        size_entropy = _entropy_from_sizes(region_sizes, normalize=True)
        # proxy entropy for rc values (discretize)
        rc_entropy = _entropy_from_sizes([int(round(x * 1000)) for x in rc_values], normalize=True) if k > 0 else 0.0
        
        summary_row = {
            "bench": bench_name,
            "exe": exe_name,
            "n_whole_nodes": int(G.number_of_nodes()),
            "n_whole_edges": int(G.number_of_edges()),
            "n_undirected_nodes": int(Gu.number_of_nodes()),
            "n_undirected_edges": int(Gu.number_of_edges()),
            # sndp stats
            "sndp_mode": sndp_stats.mode,
            "sndp_degree_threshold": sndp_stats.threshold,
            "sndp_mean": sndp_stats.mean,
            "sndp_std": sndp_stats.std,
            "sndp_median": sndp_stats.median,
            "sndp_mad": sndp_stats.mad,
            "sndp_q1": sndp_stats.q1,
            "sndp_q3": sndp_stats.q3,
            "sndp_iqr": sndp_stats.iqr,
            "n_pruned_hubs": sndp_stats.pruned,
            "pruned_hub_ratio": sndp_stats.pruned_frac,
            # regions
            "n_regions": n_regions_kept,
            "n_regions_total": n_regions_total,
            "n_regions_filtered_small": n_regions_filtered,
            "region_size_entropy": size_entropy,
            "rc_entropy_proxy": rc_entropy, 
            # imbalance
            "mean_rc": mean_rc,
            "var_rc": var_rc,
            "gini_rc": gini_rc,
            "cold_threshold_eps": cold_eps,
            "cold_frac": cold_frac,
        }

        # Driver–region alignment table: RC_d(Ri) = |Ri ∩ Vd| / |Ri|
        drv_region_rows: List[Dict[str, Any]] = []
        if k > 0:
            # pre-materialize regions list for speed
            regions_list = [set(R) for R in regions]

            for drv_id in g.drvList.keys():
                Vd, _Ed = g.get_driver_graph(drv_id)
                Vd_set = {int(x) for x in Vd}
                if not Vd_set:
                    continue

                for rid, R in enumerate(regions_list):
                    if not R:
                        continue
                    cov = len(R & Vd_set)
                    rc_d = cov / len(R)
                    drv_region_rows.append(
                        {
                            "bench": bench_name,
                            "exe": exe_name,
                            "driver": drv_id,
                            "region": rid,
                            "covered_in_driver": cov,
                            "rc_driver": rc_d,
                        }
                    )

        df_summary = pd.DataFrame([summary_row])
        df_regions = pd.DataFrame.from_records(region_rows) if region_rows else pd.DataFrame(
            columns=["bench", "exe", "region", "region_size", "covered_in_union", "rc_union"]
        )
        df_drv_region = pd.DataFrame.from_records(drv_region_rows) if drv_region_rows else pd.DataFrame(
            columns=["bench", "exe", "driver", "region", "covered_in_driver", "rc_driver"]
        )

        # Also expose the hub set (useful for debugging / paper appendix)
        df_hubs = pd.DataFrame(
            [
                {"bench": bench_name, "exe": exe_name, "node": int(v), "deg_total": int(deg_total[int(v)])}
                for v in sorted(V_hub)
            ]
        ) if V_hub else pd.DataFrame(columns=["bench", "exe", "node", "deg_total"])

        return AnalysisResult(
            tables={
                "summary": df_summary,
                "regions": df_regions,
                "driver_region": df_drv_region,
                "hubs": df_hubs,
            }
        )
