from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


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


def _import_nx():
    try:
        import networkx as nx  # type: ignore
    except Exception as e:
        raise RuntimeError("RQ3Modularity requires networkx (`pip install networkx`).") from e
    return nx


def _density_directed(n: int, m: int) -> float:
    if n <= 1:
        return 0.0
    return m / (n * (n - 1))


def _compute_modularity_undirected(nx, Gu) -> Tuple[float, int, float, float]:
    """
    Returns (Q, num_comms, largest_comm_ratio, comm_entropy_norm).
    Uses greedy modularity communities (no extra deps).
    """
    if Gu.number_of_nodes() <= 1 or Gu.number_of_edges() == 0:
        return 0.0, 0, 0.0, 0.0

    from networkx.algorithms.community import greedy_modularity_communities, modularity

    comms = list(greedy_modularity_communities(Gu))
    if not comms:
        return 0.0, 0, 0.0, 0.0

    Q = float(modularity(Gu, comms))
    sizes = [len(c) for c in comms]
    num = len(sizes)
    largest_ratio = (max(sizes) / Gu.number_of_nodes()) if Gu.number_of_nodes() else 0.0
    ent = _entropy_from_sizes(sizes, normalize=True)
    return Q, num, largest_ratio, ent


@dataclass
class DriverGraphView:
    """
    Driver-specific dynamic subgraph from the fuzzer:
      - nodes: covered/activated functions under this driver
      - edges: dynamic call edges observed under this driver (caller, callee)
    """
    driver_id: str
    nodes: Set[Any]
    edges: Set[Tuple[Any, Any]]  # dynamic edges

def _build_whole_subgraph(nx, g):
    nodes, edges = g.get_whole_graph()
    G = nx.DiGraph()
    # Keep isolated nodes too (important for correct |V|)
    G.add_nodes_from(int(n) for n in nodes)
    # Add edges (optionally filter self-loops)
    G.add_edges_from((int(u), int(v)) for (u, v) in edges if int(u) != int(v))
    return G

def _build_driver_subgraph(nx, dv: DriverGraphView, backbone: Optional[Any] = None):
    """
    Build Gd from dynamic edges. If backbone (static callgraph) is provided,
    we optionally intersect edges with the backbone edges to keep a shared reference.
    """
    Vd = set(dv.nodes)
    if not Vd:
        return nx.DiGraph()

    Gd = nx.DiGraph()
    Gd.add_nodes_from(Vd)

    # Keep only edges whose endpoints are in Vd
    Ed = [(u, v) for (u, v) in dv.edges if u in Vd and v in Vd]

    # Optional: enforce "shared backbone" (recommended if you still claim projection)
    if backbone is not None:
        try:
            backbone_edge_set = set(backbone.edges())
            Ed = [(u, v) for (u, v) in Ed if (u, v) in backbone_edge_set]
        except Exception:
            # if backbone isn't a networkx graph, just skip filtering
            pass

    Gd.add_edges_from(Ed)
    return Gd


class RQ3Modularity(Analyzer):
    key = "rq3_modularity"
    description = "RQ3: structural organization & modularity of driver-induced subgraphs"

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        nx = _import_nx()
        g  = ctx.ensure_drvgraph()

        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name   = exe_dir.name

        backbone = _build_whole_subgraph(nx, g)
        V = backbone.number_of_nodes() if backbone is not None else 0
        E = backbone.number_of_edges() if backbone is not None else 0

        records: List[Dict[str, Any]] = []

        for drv_id in g.drvList.keys():
            # a tuple of (node_list, edge_list)
            nodes, edges = g.get_driver_graph(drv_id)

            view = DriverGraphView(driver_id=drv_id, nodes=nodes, edges=edges)
            Gd = _build_driver_subgraph(nx, view, backbone=backbone)

            n = Gd.number_of_nodes()
            m = Gd.number_of_edges()
            dens = _density_directed(n, m)

            # Weak components on directed graph
            if n == 0:
                wcc_sizes: List[int] = []
                k_wcc = 0
                lcc_ratio = 0.0
                wcc_ent = 0.0
            else:
                wcc = list(nx.weakly_connected_components(Gd))
                wcc_sizes = [len(c) for c in wcc]
                k_wcc = len(wcc_sizes)
                lcc_ratio = (max(wcc_sizes) / n) if wcc_sizes else 0.0
                wcc_ent = _entropy_from_sizes(wcc_sizes, normalize=True)

            # “Glue” features + modularity on undirected projection
            Gu = nx.Graph(Gd)
            if Gu.number_of_nodes() >= 2 and Gu.number_of_edges() > 0:
                try:
                    art_points = set(nx.articulation_points(Gu))
                    bridges = list(nx.bridges(Gu))
                    art_ratio = len(art_points) / Gu.number_of_nodes()
                    bridge_ratio = len(bridges) / Gu.number_of_edges()
                except Exception:
                    art_ratio = 0.0
                    bridge_ratio = 0.0
            else:
                art_ratio = 0.0
                bridge_ratio = 0.0

            Q, num_comms, largest_comm_ratio, comm_ent = _compute_modularity_undirected(nx, Gu)

            records.append(
                {
                    "bench": bench_name,
                    "exe": exe_name,
                    "driver": drv_id,
                    # size
                    "n_nodes": n,
                    "n_edges": m,
                    "node_ratio": (n / V) if V else 0.0,
                    "edge_ratio": (m / E) if E else 0.0,
                    # organization
                    "density": dens,
                    "wcc_count": k_wcc,
                    "lcc_ratio": lcc_ratio,
                    "wcc_entropy": wcc_ent,
                    # modularity
                    "modularity_Q": Q,
                    "community_count": num_comms,
                    "largest_comm_ratio": largest_comm_ratio,
                    "community_entropy": comm_ent,
                    # glue
                    "articulation_ratio": art_ratio,
                    "bridge_ratio": bridge_ratio,
                }
            )

        df = pd.DataFrame.from_records(records)
        return AnalysisResult(
            tables={"driver_metrics": df},
        )