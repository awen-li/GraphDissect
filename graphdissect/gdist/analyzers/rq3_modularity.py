from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple
import math
import pandas as pd
from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


class RQ2Modularity(Analyzer):
    key = "rq2"
    description = "RQ2: structural organization & modularity of driver-induced subgraphs"

    def __init__(self, size_bins: Sequence[int] = (10, 25, 50, 100, 200, 500, 1000)):
        # bins for distribution summaries
        self.size_bins = list(size_bins)
        self.func_cov: Dict[int, Set[str]] = {}

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        g = ctx.ensure_drvgraph()
        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        # (1) per-driver function set (driver-induced subgraph nodes)
        self.func_cov = self._compute_function_coverage(g)

        # (2) shared call-graph backbone edges (whole-program)
        backbone_edges = list(self._iter_backbone_edges(g))  # List[(caller, callee)] as strings

        # Prebuild an adjacency map for faster induced-edge filtering
        adj_out = self._build_out_adj(backbone_edges)  # caller -> set(callee)

        # (3) per-driver metrics
        df_drivers = self._build_driver_table(
            exe_dir=exe_dir,
            g=g,
            bench_name=bench_name,
            exe_name=exe_name,
            adj_out=adj_out,
        )

        df_summary = self._build_summary_table(exe_dir, bench_name, exe_name, df_drivers)
        df_dist = self._build_distribution_tables(bench_name, exe_name, df_drivers)

        return AnalysisResult(tables={
            "summary": df_summary,
            "drivers": df_drivers,
            "size_connectivity_distribution": df_dist,
        })

    # ----------------------------
    # (1) Function coverage (nodes)
    # ----------------------------
    def _compute_function_coverage(self, g) -> Dict[int, Set[str]]:
        out: Dict[int, Set[str]] = {}
        for drv_id in g.drvList.keys():
            did = int(drv_id)
            cov_functions = g.get_driver_graph(drv_id)  # should exist
            out[did] = set(map(str, cov_functions))
        return out

    # ----------------------------
    # (2) Backbone extraction (edges)
    # ----------------------------
    def _iter_backbone_edges(self, g) -> Iterable[Tuple[str, str]]:
        """
        Return (src, dst) edges of the shared whole-program call graph backbone.

        This tries a few common shapes:
          - g.cgGraph.edges / g.cgGraph.edgeList
          - g.callgraph.edges
          - g.graph.edges
          - g.edges
        where each edge may be:
          - tuple(src, dst)
          - object with .src/.dst or .caller/.callee or .u/.v
        """
        candidates = [
            getattr(g, "cgGraph", None),
            getattr(g, "callgraph", None),
            getattr(g, "graph", None),
            g,
        ]

        def edge_iter(obj) -> Optional[Iterable]:
            if obj is None:
                return None
            for attr in ("edges", "edgeList", "edges_list", "E"):
                if hasattr(obj, attr):
                    return getattr(obj, attr)
            return None

        def as_pair(e) -> Optional[Tuple[str, str]]:
            if e is None:
                return None
            if isinstance(e, tuple) and len(e) == 2:
                return (str(e[0]), str(e[1]))
            for a, b in (("src", "dst"), ("caller", "callee"), ("u", "v"), ("from_", "to"), ("frm", "to")):
                if hasattr(e, a) and hasattr(e, b):
                    return (str(getattr(e, a)), str(getattr(e, b)))
            return None

        for obj in candidates:
            it = edge_iter(obj)
            if it is None:
                continue

            # Some graphs store edges in dicts/sets; normalize to iterable of edges
            if isinstance(it, dict):
                iterable = it.values()
            else:
                iterable = it

            yielded = 0
            for e in iterable:
                p = as_pair(e)
                if p is None:
                    continue
                yielded += 1
                yield p

            if yielded > 0:
                return  # stop at the first graph object that yields edges

        # If we reach here, we failed to find edges. Return empty iterable.
        return

    def _build_out_adj(self, edges: Iterable[Tuple[str, str]]) -> Dict[str, Set[str]]:
        adj: Dict[str, Set[str]] = {}
        for u, v in edges:
            adj.setdefault(u, set()).add(v)
        return adj

    # ----------------------------
    # (3) Per-driver metrics
    # ----------------------------
    def _induced_edge_count(self, nodes: Set[str], adj_out: Dict[str, Set[str]]) -> int:
        """Count directed edges (u->v) where u and v are both in nodes."""
        m = 0
        for u in nodes:
            outs = adj_out.get(u)
            if not outs:
                continue
            # count only those targets also in nodes
            # (fast membership in set)
            for v in outs:
                if v in nodes and v != u:
                    m += 1
        return m

    def _weakly_connected_components(self, nodes: Set[str], adj_out: Dict[str, Set[str]]) -> List[Set[str]]:
        """
        Compute weakly connected components: treat call edges as undirected between nodes in the induced subgraph.
        """
        if not nodes:
            return []

        # build undirected adjacency on-the-fly
        und: Dict[str, Set[str]] = {n: set() for n in nodes}
        for u in nodes:
            outs = adj_out.get(u)
            if not outs:
                continue
            for v in outs:
                if v in nodes and v != u:
                    und[u].add(v)
                    und[v].add(u)

        seen: Set[str] = set()
        comps: List[Set[str]] = []
        for n in nodes:
            if n in seen:
                continue
            stack = [n]
            comp: Set[str] = set()
            seen.add(n)
            while stack:
                x = stack.pop()
                comp.add(x)
                for y in und.get(x, ()):
                    if y not in seen:
                        seen.add(y)
                        stack.append(y)
            comps.append(comp)
        return comps

    def _build_driver_table(
        self,
        exe_dir: Path,
        g,
        bench_name: str,
        exe_name: str,
        adj_out: Dict[str, Set[str]],
    ) -> pd.DataFrame:
        # Use driver order if you have it; otherwise fallback to drvList keys
        order: List[int] = []
        try:
            drivers_dir = exe_dir / "drivers"
            order = _load_driver_order(drivers_dir)  # your existing helper
        except Exception:
            order = []
        if not order:
            order = [int(k) for k in g.drvList.keys()]

        rows: List[Dict[str, object]] = []
        for did in order:
            nodes = self.func_cov.get(int(did), set())
            n = len(nodes)
            m = self._induced_edge_count(nodes, adj_out) if n >= 2 else 0

            # directed density on n nodes (excluding self-loops)
            denom = n * (n - 1)
            density = (m / denom) if denom > 0 else 0.0

            comps = self._weakly_connected_components(nodes, adj_out) if n > 0 else []
            num_cc = len(comps)
            lcc = max((len(c) for c in comps), default=0)
            lcc_ratio = (lcc / n) if n > 0 else 0.0
            avg_cc = (n / num_cc) if num_cc > 0 else 0.0

            drv = g.drvList.get(did) or g.drvList.get(str(did))
            drv_name = getattr(drv, "name", str(did)) if drv is not None else str(did)

            rows.append({
                "bench": bench_name,
                "exe": exe_name,
                "driver_id": int(did),
                "driver_name": drv_name,
                "n_nodes": int(n),
                "n_edges": int(m),
                "density": float(density),
                "num_cc": int(num_cc),
                "lcc_size": int(lcc),
                "lcc_ratio": float(lcc_ratio),
                "avg_cc_size": float(avg_cc),
            })

        return pd.DataFrame(rows)

    # ----------------------------
    # (4) Summary + distributions
    # ----------------------------
    def _build_summary_table(self, exe_dir: Path, bench_name: str, exe_name: str, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame([{
                "bench": bench_name,
                "exe": exe_name,
                "exe_dir": str(exe_dir),
                "num_drivers": 0,
            }])

        return pd.DataFrame([{
            "bench": bench_name,
            "exe": exe_name,
            "exe_dir": str(exe_dir),
            "num_drivers": int(len(df)),
            "nodes_min": int(df["n_nodes"].min()),
            "nodes_median": float(df["n_nodes"].median()),
            "nodes_max": int(df["n_nodes"].max()),
            "density_median": float(df["density"].median()),
            "num_cc_median": float(df["num_cc"].median()),
            "lcc_ratio_median": float(df["lcc_ratio"].median()),
        }])

    def _build_distribution_tables(self, bench: str, exe: str, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["bench", "exe", "bucket", "count", "density_median", "num_cc_median", "lcc_ratio_median"])

        # bucket by subgraph size
        bins = [-math.inf] + list(self.size_bins) + [math.inf]
        labels = []
        for i in range(1, len(bins)):
            lo, hi = bins[i-1], bins[i]
            if lo == -math.inf:
                labels.append(f"<= {hi}")
            elif hi == math.inf:
                labels.append(f"> {int(lo)}")
            else:
                labels.append(f"{int(lo)+1}–{int(hi)}")

        tmp = df.copy()
        tmp["bucket"] = pd.cut(tmp["n_nodes"], bins=bins, labels=labels, include_lowest=True)

        agg = tmp.groupby("bucket", dropna=False).agg(
            count=("driver_id", "count"),
            density_median=("density", "median"),
            num_cc_median=("num_cc", "median"),
            lcc_ratio_median=("lcc_ratio", "median"),
        ).reset_index()

        agg.insert(0, "exe", exe)
        agg.insert(0, "bench", bench)
        return agg
