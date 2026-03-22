from __future__ import annotations

from typing import Dict, List, Set, Tuple

import pandas as pd
import networkx as nx

from gdist.analyzers.analyzer import Analyzer, AnalysisContext, AnalysisResult


EdgeKey = Tuple[int, int]


class RQ5UnderExploredRegions(Analyzer):
    """
    RQ5: Identify structural regions that remain under-explored after
         union multi-driver fuzzing.

    Main outputs:
      - summary: backbone / union coverage / region statistics
      - regions: per-region coverage metrics
      - region_distribution: summary stats over region coverage
      - candidate_gaps: lowest-coverage regions for case study
      - region_functions: one row per region with function ids/names
                          serialized for CSV export

    Performance-oriented design:
      - community detection is run per weakly connected component
      - small components are kept as a single region
      - Louvain is run on an undirected projection
      - no giant per-node membership table by default
    """

    key = "rq5"
    description = "RQ5: under-explored structural regions after union multi-driver fuzzing"

    def __init__(
        self,
        top_k_regions: int = 25,
        min_region_size: int = 5,
        low_cov_threshold: float = 0.20,
        resolution: float = 1.0,
        seed: int = 0,
        min_component_size_for_louvain: int = 20,
        max_component_size_for_louvain: int = 50_000,
    ):
        self.top_k_regions = int(top_k_regions)
        self.min_region_size = int(min_region_size)
        self.low_cov_threshold = float(low_cov_threshold)
        self.resolution = float(resolution)
        self.seed = int(seed)
        self.min_component_size_for_louvain = int(min_component_size_for_louvain)
        self.max_component_size_for_louvain = int(max_component_size_for_louvain)

        self.backbone_nodes: Set[int] = set()
        self.backbone_edges: Set[EdgeKey] = set()
        self.union_cov: Set[int] = set()
        self._name_cache: Dict[int, str] = {}

    def compute(self, ctx: AnalysisContext) -> AnalysisResult:
        g = ctx.ensure_drvgraph()
        exe_dir = ctx.benchDir
        bench_name = exe_dir.parent.name
        exe_name = exe_dir.name

        # (1) whole-program backbone
        self.backbone_nodes, self.backbone_edges = self._load_backbone(g)

        # (2) union multi-driver node coverage
        self.union_cov = self._compute_union_node_coverage(g, self.backbone_nodes)

        # (3) build graph + detect regions
        G = self._build_directed_graph(self.backbone_nodes, self.backbone_edges)
        regions = self._detect_regions_fast(G)

        # (4) tables
        df_regions = self._build_region_table(bench_name, exe_name, G, regions)
        df_summary = self._build_summary(bench_name, exe_name, G, df_regions)
        df_dist = self._build_region_distribution(bench_name, exe_name, df_regions)
        df_gaps = self._build_candidate_gaps(df_regions)
        df_region_functions = self._build_region_functions_table(
            bench_name, exe_name, g, regions, df_regions
        )

        return AnalysisResult(
            tables={
                "summary": df_summary,
                "regions": df_regions,
                "region_distribution": df_dist,
                "candidate_gaps": df_gaps,
                "region_functions": df_region_functions,
            }
        )

    # ----------------------------
    # Backbone + union coverage
    # ----------------------------
    def _load_backbone(self, g) -> Tuple[Set[int], Set[EdgeKey]]:
        nodes, edges = g.get_whole_graph()

        V: Set[int] = set(int(n) for n in nodes) if nodes is not None else set()
        E: Set[EdgeKey] = set()

        if edges is not None:
            for (u, v) in edges:
                iu, iv = int(u), int(v)
                if iu == iv:
                    continue
                if iu not in V or iv not in V:
                    continue
                E.add((iu, iv))

        return V, E

    def _compute_union_node_coverage(self, g, backbone_nodes: Set[int]) -> Set[int]:
        covered: Set[int] = set()

        for drv_id in g.drvList.keys():
            nodes, _ = g.get_driver_graph(drv_id)
            if nodes is None:
                continue
            for n in nodes:
                nid = int(n)
                if nid in backbone_nodes:
                    covered.add(nid)

        return covered

    # ----------------------------
    # Graph construction
    # ----------------------------
    @staticmethod
    def _build_directed_graph(nodes: Set[int], edges: Set[EdgeKey]) -> nx.DiGraph:
        G = nx.DiGraph()
        G.add_nodes_from(nodes)
        G.add_edges_from(edges)
        return G

    # ----------------------------
    # Region detection
    # ----------------------------
    def _detect_regions_fast(self, G: nx.DiGraph) -> List[Set[int]]:
        """
        Faster region detection:
          1) split into weakly connected components
          2) for each component:
             - keep small components as one region
             - run Louvain on undirected projection for medium components
             - fall back to label propagation for very large components
        """
        if G.number_of_nodes() == 0:
            return []

        regions: List[Set[int]] = []

        for comp_nodes in nx.weakly_connected_components(G):
            comp_nodes = set(int(n) for n in comp_nodes)
            comp_size = len(comp_nodes)

            if comp_size == 0:
                continue

            # Tiny components: no need to run community detection
            if comp_size < self.min_component_size_for_louvain:
                regions.append(comp_nodes)
                continue

            sub_u = G.subgraph(comp_nodes).to_undirected()

            # Medium components: Louvain
            if comp_size <= self.max_component_size_for_louvain:
                try:
                    comms = nx.algorithms.community.louvain_communities(
                        sub_u,
                        resolution=self.resolution,
                        seed=self.seed,
                    )
                    for comm in comms:
                        comm_set = set(int(n) for n in comm)
                        if comm_set:
                            regions.append(comm_set)
                    continue
                except Exception:
                    pass

            # Very large components or Louvain failure: label propagation fallback
            try:
                comms = nx.algorithms.community.asyn_lpa_communities(
                    sub_u,
                    weight=None,
                    seed=self.seed,
                )
                for comm in comms:
                    comm_set = set(int(n) for n in comm)
                    if comm_set:
                        regions.append(comm_set)
            except Exception:
                # Last fallback: keep the whole component as one region
                regions.append(comp_nodes)

        regions.sort(key=lambda s: (-len(s), min(s) if s else -1))
        return regions

    # ----------------------------
    # Region metrics
    # ----------------------------
    def _build_region_table(
        self,
        bench: str,
        exe: str,
        G: nx.DiGraph,
        regions: List[Set[int]],
    ) -> pd.DataFrame:
        rows: List[Dict[str, object]] = []

        for ridx, region_nodes in enumerate(regions, start=1):
            covered_nodes = region_nodes & self.union_cov
            uncovered_nodes = region_nodes - self.union_cov

            size = len(region_nodes)
            covered = len(covered_nodes)
            uncovered = len(uncovered_nodes)
            rc = (covered / size) if size > 0 else 0.0

            sub = G.subgraph(region_nodes)
            internal_edges = int(sub.number_of_edges())

            boundary_out_edges = 0
            for u in region_nodes:
                for v in G.successors(u):
                    if v not in region_nodes:
                        boundary_out_edges += 1

            boundary_in_edges = 0
            for u in region_nodes:
                for v in G.predecessors(u):
                    if v not in region_nodes:
                        boundary_in_edges += 1

            rows.append(
                {
                    "bench": bench,
                    "exe": exe,
                    "region_id": int(ridx),
                    "region_size": int(size),
                    "covered_nodes": int(covered),
                    "uncovered_nodes": int(uncovered),
                    "region_coverage": float(rc),
                    "internal_cg_edges": int(internal_edges),
                    "boundary_out_edges": int(boundary_out_edges),
                    "boundary_in_edges": int(boundary_in_edges),
                    "is_low_coverage": bool(rc <= self.low_cov_threshold),
                }
            )

        if not rows:
            return pd.DataFrame(
                columns=[
                    "bench",
                    "exe",
                    "region_id",
                    "region_size",
                    "covered_nodes",
                    "uncovered_nodes",
                    "region_coverage",
                    "internal_cg_edges",
                    "boundary_out_edges",
                    "boundary_in_edges",
                    "is_low_coverage",
                ]
            )

        return (
            pd.DataFrame(rows)
            .sort_values(
                by=["region_coverage", "uncovered_nodes", "region_size"],
                ascending=[True, False, False],
            )
            .reset_index(drop=True)
        )

    # ----------------------------
    # Summaries
    # ----------------------------
    def _build_summary(
        self,
        bench: str,
        exe: str,
        G: nx.DiGraph,
        df_regions: pd.DataFrame,
    ) -> pd.DataFrame:
        total_nodes = int(G.number_of_nodes())
        total_edges = int(G.number_of_edges())
        covered_union = int(len(self.union_cov))
        union_cov_ratio = (covered_union / total_nodes) if total_nodes > 0 else 0.0

        row = {
            "bench": bench,
            "exe": exe,
            "backbone_nodes": total_nodes,
            "backbone_edges": total_edges,
            "union_covered_nodes": covered_union,
            "union_coverage": float(union_cov_ratio),
            "num_regions": int(len(df_regions)),
            "low_cov_threshold": float(self.low_cov_threshold),
            "num_low_cov_regions": int(df_regions["is_low_coverage"].sum()) if not df_regions.empty else 0,
            "share_low_cov_regions": float(df_regions["is_low_coverage"].mean()) if not df_regions.empty else 0.0,
            "avg_region_size": float(df_regions["region_size"].mean()) if not df_regions.empty else 0.0,
            "median_region_size": float(df_regions["region_size"].median()) if not df_regions.empty else 0.0,
            "avg_region_coverage": float(df_regions["region_coverage"].mean()) if not df_regions.empty else 0.0,
            "median_region_coverage": float(df_regions["region_coverage"].median()) if not df_regions.empty else 0.0,
        }
        return pd.DataFrame([row])

    def _build_region_distribution(
        self, bench: str, exe: str, df_regions: pd.DataFrame
    ) -> pd.DataFrame:
        if df_regions.empty:
            return pd.DataFrame([{"bench": bench, "exe": exe, "num_regions": 0}])

        s = df_regions["region_coverage"]

        row = {
            "bench": bench,
            "exe": exe,
            "num_regions": int(len(df_regions)),
            "rc_min": float(s.min()),
            "rc_p25": float(s.quantile(0.25)),
            "rc_median": float(s.quantile(0.50)),
            "rc_p75": float(s.quantile(0.75)),
            "rc_p90": float(s.quantile(0.90)),
            "rc_max": float(s.max()),
            "share_rc_eq_0": float((s == 0.0).mean()),
            "share_rc_le_0_1": float((s <= 0.1).mean()),
            "share_rc_le_0_2": float((s <= 0.2).mean()),
            "share_rc_le_0_5": float((s <= 0.5).mean()),
        }
        return pd.DataFrame([row])

    def _build_candidate_gaps(self, df_regions: pd.DataFrame) -> pd.DataFrame:
        if df_regions.empty:
            return df_regions.copy()

        out = df_regions[df_regions["region_size"] >= self.min_region_size].copy()
        out = out.sort_values(
            by=["region_coverage", "uncovered_nodes", "region_size"],
            ascending=[True, False, False],
        ).head(self.top_k_regions)

        out.insert(0, "gap_rank", range(1, len(out) + 1))
        return out.reset_index(drop=True)

    # ----------------------------
    # Region -> function-name CSV table
    # ----------------------------
    def _get_node_name(self, g, node_id: int) -> str:
        node_id = int(node_id)
        if node_id in self._name_cache:
            return self._name_cache[node_id]

        try:
            name = g.get_node_name(node_id)
        except Exception:
            name = str(node_id)

        if name is None:
            name = str(node_id)

        name = str(name)
        self._name_cache[node_id] = name
        return name
    
    def _clean_csv_text(self, s: object) -> str:
        if s is None:
            return ""
        s = str(s)
        s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
        s = " ".join(s.split())
        return s


    def _join_limited(self, values, sep: str = ";", limit: int = 500) -> str:
        out = []
        for v in values[:limit]:
            s = self._clean_csv_text(v)
            if sep in s:
                s = s.replace(sep, "/")
            out.append(s)
        return sep.join(out)


    def _build_region_functions_table(
        self,
        bench: str,
        exe: str,
        g,
        regions: List[Set[int]],
        df_regions: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        One row per region, suitable for CSV export.

        Keep full counts, but only store up to 500 IDs/names in packed columns.
        Packed columns still use ';'.
        """
        columns = [
            "bench",
            "exe",
            "region_id",
            "region_size",
            "region_coverage",
            "covered_nodes",
            "uncovered_nodes",
            "function_count",
            "covered_function_count",
            "uncovered_function_count",
            "stored_function_count",
            "stored_covered_function_count",
            "stored_uncovered_function_count",
            "function_ids",
            "function_names",
            "covered_function_ids",
            "covered_function_names",
            "uncovered_function_ids",
            "uncovered_function_names",
        ]

        if df_regions.empty:
            return pd.DataFrame(columns=columns)

        metrics_by_region = {
            int(row["region_id"]): row for _, row in df_regions.iterrows()
        }

        rows: List[Dict[str, object]] = []
        STORE_LIMIT = 1500

        for ridx, region_nodes in enumerate(regions, start=1):
            sorted_nodes = sorted(int(n) for n in region_nodes)
            m = metrics_by_region[int(ridx)]

            covered_ids = [n for n in sorted_nodes if n in self.union_cov]
            uncovered_ids = [n for n in sorted_nodes if n not in self.union_cov]

            name_by_id = {n: self._get_node_name(g, n) for n in sorted_nodes}

            all_names = [name_by_id[n] for n in sorted_nodes]
            covered_names = [name_by_id[n] for n in covered_ids]
            uncovered_names = [name_by_id[n] for n in uncovered_ids]

            rows.append(
                {
                    "bench": bench,
                    "exe": exe,
                    "region_id": int(ridx),
                    "region_size": int(m["region_size"]),
                    "region_coverage": float(m["region_coverage"]),
                    "covered_nodes": int(m["covered_nodes"]),
                    "uncovered_nodes": int(m["uncovered_nodes"]),

                    "function_count": int(len(sorted_nodes)),
                    "covered_function_count": int(len(covered_ids)),
                    "uncovered_function_count": int(len(uncovered_ids)),

                    "stored_function_count": int(len(sorted_nodes)),
                    "stored_covered_function_count": int(len(covered_ids)),
                    "stored_uncovered_function_count": int(len(uncovered_ids)),

                    "function_ids": self._join_limited(sorted_nodes, sep=";", limit=10000),
                    "function_names": self._join_limited(all_names, sep=";", limit=STORE_LIMIT),

                    "covered_function_ids": self._join_limited(covered_ids, sep=";", limit=10000),
                    "covered_function_names": self._join_limited(covered_names, sep=";", limit=STORE_LIMIT),

                    "uncovered_function_ids": self._join_limited(uncovered_ids, sep=";", limit=10000),
                    "uncovered_function_names": self._join_limited(uncovered_names, sep=";", limit=STORE_LIMIT),
                }
            )

        return (
            pd.DataFrame(rows, columns=columns)
            .sort_values(
                by=["region_coverage", "uncovered_nodes", "region_size"],
                ascending=[True, False, False],
            )
            .reset_index(drop=True)
        )
        