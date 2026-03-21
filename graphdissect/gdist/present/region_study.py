from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

import math
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from gdist.graph.graph import DrvGraph

EdgeKey = Tuple[int, int]


@dataclass
class RegionInfo:
    bench: str
    exe: str
    region_id: int
    region_size: int
    covered_nodes: int
    uncovered_nodes: int
    region_coverage: float
    function_ids: List[int]
    function_names: List[str]
    covered_function_ids: List[int]
    covered_function_names: List[str]
    uncovered_function_ids: List[int]
    uncovered_function_names: List[str]


class RegionStudyGenerator:
    """
    Generate RQ5 case-study artifacts for one executable.

    Inputs:
      - rq5_present__candidate_gaps.csv
      - rq5_present__region_functions.csv
      - backbone graph loader for the selected executable

    Outputs:
      - rq5_case__{bench}__{exe}__selected_regions.csv
      - rq5_case__{bench}__{exe}__region_edges.csv
      - rq5_case__{bench}__{exe}__annotation_template.csv
      - rq5_case__{bench}__{exe}__figure.pdf
      - rq5_case__{bench}__{exe}__figure.png
    """

    def __init__(
        self,
        benchdir: str = "",
        out_dir: str = "",
        bench: str = "",
        exe: str = "",
        top_k_gap_regions: int = 5,
    ):
        self.benchdir = benchdir
        self.bench = bench
        self.exe = exe
        self.top_k_gap_regions = top_k_gap_regions

        self.present_dir = str(Path(self.benchdir) / "paper_artifacts" / "rq5")
        self.out_dir = out_dir if out_dir else str(Path(self.present_dir) / "case_study")

        # adjust this if DrvGraph expects a different path
        self.g = DrvGraph(benchPath=f"{self.benchdir}/{self.bench}", binaryName=self.exe)

    include_context_neighbors: bool = True
    max_context_neighbors: int = 8
    max_regions_in_figure: int = 12
    rep_uncovered_per_region: int = 2
    rep_covered_per_region: int = 1
    layout_seed: int = 7
    fig_width: float = 11.0
    fig_height: float = 8.0

    def run(self) -> None:
        out_dir = Path(self.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        df_gaps = pd.read_csv(Path(self.present_dir) / "rq5_present__candidate_gaps.csv")
        df_funcs = pd.read_csv(Path(self.present_dir) / "rq5_present__region_functions.csv")

        df_gaps = self._normalize(df_gaps)
        df_funcs = self._normalize(df_funcs)

        df_gaps = self._filter_exe(df_gaps)
        df_funcs = self._filter_exe(df_funcs)

        if df_gaps.empty:
            raise ValueError(f"No candidate gaps found for ({self.bench}, {self.exe})")
        if df_funcs.empty:
            raise ValueError(f"No region-function rows found for ({self.bench}, {self.exe})")

        # Build region info map from enriched region_functions.csv
        region_info = self._build_region_info(df_funcs)

        # Load backbone graph from the project graph loader
        backbone = self._build_backbone_graph(self.g)

        # Collapse full backbone to region-level graph
        func_to_region = self._build_func_to_region(region_info)
        region_graph = self._build_region_graph(backbone, func_to_region)

        # Auto-select regions from candidate gaps
        selected_gap_ids = self._select_gap_regions(df_gaps)
        display_region_ids = self._expand_display_regions(
            selected_gap_ids=selected_gap_ids,
            region_graph=region_graph,
        )

        # Trim if too large
        if len(display_region_ids) > self.max_regions_in_figure:
            display_region_ids = self._trim_display_regions(
                selected_gap_ids=selected_gap_ids,
                display_region_ids=display_region_ids,
                region_graph=region_graph,
            )

        # Representative functions for labels
        rep_map = self._build_representative_functions(
            backbone=backbone,
            region_graph=region_graph,
            region_info=region_info,
            display_region_ids=display_region_ids,
        )

        # Optional existing manual annotation
        annot_path = out_dir / f"rq5_case__{self.bench}__{self.exe}__annotation_template.csv"
        df_annot = self._load_or_init_annotations(
            annot_path=annot_path,
            region_ids=display_region_ids,
            region_info=region_info,
            selected_gap_ids=selected_gap_ids,
            rep_map=rep_map,
        )

        # Save selected region table
        self._write_selected_regions_csv(
            out_path=out_dir / f"rq5_case__{self.bench}__{self.exe}__selected_regions.csv",
            region_info=region_info,
            region_ids=display_region_ids,
            selected_gap_ids=selected_gap_ids,
            rep_map=rep_map,
            df_annot=df_annot,
        )

        # Save region edge table
        self._write_region_edges_csv(
            out_path=out_dir / f"rq5_case__{self.bench}__{self.exe}__region_edges.csv",
            region_graph=region_graph,
            region_ids=display_region_ids,
        )

        # Draw figure
        fig_pdf = out_dir / f"rq5_case__{self.bench}__{self.exe}__figure.pdf"
        fig_png = out_dir / f"rq5_case__{self.bench}__{self.exe}__figure.png"
        self._draw_figure(
            out_pdf=fig_pdf,
            out_png=fig_png,
            region_graph=region_graph,
            region_info=region_info,
            region_ids=display_region_ids,
            selected_gap_ids=selected_gap_ids,
            rep_map=rep_map,
            df_annot=df_annot,
        )

    # ------------------------------------------------------------------
    # Loading / normalization
    # ------------------------------------------------------------------
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        if "bench" in out.columns:
            out["bench"] = out["bench"].astype(str)
        if "exe" in out.columns:
            out["exe"] = out["exe"].astype(str)

        numeric_cols = [
            "gap_rank",
            "region_id",
            "region_size",
            "covered_nodes",
            "uncovered_nodes",
            "region_coverage",
            "covered_function_count",
            "uncovered_function_count",
        ]
        for c in numeric_cols:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce")

        return out

    def _filter_exe(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[
            (df["bench"].astype(str) == self.bench)
            & (df["exe"].astype(str) == self.exe)
        ].copy()

    def _build_region_info(self, df_funcs: pd.DataFrame) -> Dict[int, RegionInfo]:
        out: Dict[int, RegionInfo] = {}

        for _, row in df_funcs.iterrows():
            rid = int(row["region_id"])

            out[rid] = RegionInfo(
                bench=str(row["bench"]),
                exe=str(row["exe"]),
                region_id=rid,
                region_size=int(row["region_size"]),
                covered_nodes=int(row["covered_nodes"]),
                uncovered_nodes=int(row["uncovered_nodes"]),
                region_coverage=float(row["region_coverage"]),
                function_ids=self._parse_int_list(row.get("function_ids")),
                function_names=self._parse_str_list(row.get("function_names")),
                covered_function_ids=self._parse_int_list(row.get("covered_function_ids")),
                covered_function_names=self._parse_str_list(row.get("covered_function_names")),
                uncovered_function_ids=self._parse_int_list(row.get("uncovered_function_ids")),
                uncovered_function_names=self._parse_str_list(row.get("uncovered_function_names")),
            )

        return out

    # ------------------------------------------------------------------
    # Backbone / region graph
    # ------------------------------------------------------------------
    def _build_backbone_graph(self, g_obj) -> nx.DiGraph:
        nodes, edges = g_obj.get_whole_graph()

        V: Set[int] = set(int(n) for n in nodes) if nodes is not None else set()
        G = nx.DiGraph()
        G.add_nodes_from(V)

        if edges is not None:
            for (u, v) in edges:
                iu, iv = int(u), int(v)
                if iu == iv:
                    continue
                if iu not in V or iv not in V:
                    continue
                G.add_edge(iu, iv)

        return G

    def _build_func_to_region(self, region_info: Dict[int, RegionInfo]) -> Dict[int, int]:
        func_to_region: Dict[int, int] = {}

        for rid, info in region_info.items():
            for nid in info.function_ids:
                func_to_region[int(nid)] = int(rid)

        return func_to_region

    def _build_region_graph(
        self,
        backbone: nx.DiGraph,
        func_to_region: Dict[int, int],
    ) -> nx.DiGraph:
        RG = nx.DiGraph()

        for rid in set(func_to_region.values()):
            RG.add_node(int(rid))

        for u, v in backbone.edges():
            ru = func_to_region.get(int(u))
            rv = func_to_region.get(int(v))
            if ru is None or rv is None or ru == rv:
                continue

            if RG.has_edge(ru, rv):
                RG[ru][rv]["weight"] += 1
            else:
                RG.add_edge(ru, rv, weight=1)

        return RG

    # ------------------------------------------------------------------
    # Region selection
    # ------------------------------------------------------------------
    def _select_gap_regions(self, df_gaps: pd.DataFrame) -> List[int]:
        gaps = df_gaps.copy()

        if "gap_rank" in gaps.columns and gaps["gap_rank"].notna().any():
            gaps = gaps.sort_values(["gap_rank", "region_id"], kind="mergesort")
        else:
            gaps = gaps.sort_values(
                ["region_coverage", "uncovered_nodes", "region_size", "region_id"],
                ascending=[True, False, False, True],
                kind="mergesort",
            )

        gaps = gaps.head(self.top_k_gap_regions)
        return [int(x) for x in gaps["region_id"].tolist()]

    def _expand_display_regions(
        self,
        selected_gap_ids: List[int],
        region_graph: nx.DiGraph,
    ) -> List[int]:
        region_ids: Set[int] = set(int(r) for r in selected_gap_ids)

        if not self.include_context_neighbors:
            return sorted(region_ids)

        # collect one-hop predecessors/successors as context
        neighbors: List[Tuple[int, int]] = []
        for rid in selected_gap_ids:
            if not region_graph.has_node(rid):
                continue

            for p in region_graph.predecessors(rid):
                w = int(region_graph[p][rid].get("weight", 1))
                neighbors.append((p, w))
            for s in region_graph.successors(rid):
                w = int(region_graph[rid][s].get("weight", 1))
                neighbors.append((s, w))

        # add strongest unique neighbors first
        seen: Set[int] = set(region_ids)
        ranked = sorted(neighbors, key=lambda x: (-x[1], x[0]))

        added = 0
        for nid, _ in ranked:
            nid = int(nid)
            if nid in seen:
                continue
            seen.add(nid)
            region_ids.add(nid)
            added += 1
            if added >= self.max_context_neighbors:
                break

        return sorted(region_ids)

    def _trim_display_regions(
        self,
        selected_gap_ids: List[int],
        display_region_ids: List[int],
        region_graph: nx.DiGraph,
    ) -> List[int]:
        keep: Set[int] = set(int(r) for r in selected_gap_ids)
        extras = [r for r in display_region_ids if r not in keep]

        scored: List[Tuple[int, int]] = []
        for rid in extras:
            score = 0
            for x in selected_gap_ids:
                if region_graph.has_edge(rid, x):
                    score += int(region_graph[rid][x].get("weight", 1))
                if region_graph.has_edge(x, rid):
                    score += int(region_graph[x][rid].get("weight", 1))
            scored.append((rid, score))

        scored = sorted(scored, key=lambda x: (-x[1], x[0]))
        budget = max(0, self.max_regions_in_figure - len(keep))

        for rid, _ in scored[:budget]:
            keep.add(int(rid))

        return sorted(keep)

    # ------------------------------------------------------------------
    # Representative functions
    # ------------------------------------------------------------------
    def _build_representative_functions(
        self,
        backbone: nx.DiGraph,
        region_graph: nx.DiGraph,
        region_info: Dict[int, RegionInfo],
        display_region_ids: Iterable[int],
    ) -> Dict[int, Dict[str, List[str]]]:
        out: Dict[int, Dict[str, List[str]]] = {}

        func_to_region = self._build_func_to_region(region_info)

        for rid in display_region_ids:
            info = region_info[int(rid)]

            uncov = self._rank_function_names(
                backbone=backbone,
                func_ids=info.uncovered_function_ids,
                func_names=info.uncovered_function_names,
                func_to_region=func_to_region,
                region_id=rid,
                top_k=self.rep_uncovered_per_region,
            )
            cov = self._rank_function_names(
                backbone=backbone,
                func_ids=info.covered_function_ids,
                func_names=info.covered_function_names,
                func_to_region=func_to_region,
                region_id=rid,
                top_k=self.rep_covered_per_region,
            )

            out[int(rid)] = {
                "uncovered": uncov,
                "covered": cov,
            }

        return out

    def _rank_function_names(
        self,
        backbone: nx.DiGraph,
        func_ids: List[int],
        func_names: List[str],
        func_to_region: Dict[int, int],
        region_id: int,
        top_k: int,
    ) -> List[str]:
        if not func_ids or not func_names:
            return []

        pairs = list(zip(func_ids, func_names))
        scored: List[Tuple[float, str]] = []

        for fid, name in pairs:
            fid = int(fid)
            name = str(name)

            deg = backbone.in_degree(fid) + backbone.out_degree(fid) if backbone.has_node(fid) else 0

            boundary = 0
            if backbone.has_node(fid):
                for succ in backbone.successors(fid):
                    if func_to_region.get(int(succ)) != int(region_id):
                        boundary += 1
                for pred in backbone.predecessors(fid):
                    if func_to_region.get(int(pred)) != int(region_id):
                        boundary += 1

            name_score = self._name_informativeness_score(name)
            score = (3.0 * boundary) + (1.5 * deg) + name_score

            scored.append((score, name))

        scored.sort(key=lambda x: (-x[0], x[1]))
        out: List[str] = []
        used: Set[str] = set()

        for _, name in scored:
            if name in used:
                continue
            used.add(name)
            out.append(name)
            if len(out) >= top_k:
                break

        return out

    # ------------------------------------------------------------------
    # Annotation sheet / csv exports
    # ------------------------------------------------------------------
    def _load_or_init_annotations(
        self,
        annot_path: Path,
        region_ids: Iterable[int],
        region_info: Dict[int, RegionInfo],
        selected_gap_ids: Iterable[int],
        rep_map: Dict[int, Dict[str, List[str]]],
    ) -> pd.DataFrame:
        selected_set = {int(r) for r in selected_gap_ids}
        region_ids = sorted({int(r) for r in region_ids})

        id_cols = ["bench", "exe", "region_id"]
        auto_cols = ["is_selected_gap", "region_coverage", "coverage_class"]
        default_editable_cols = [
            "candidate_uncovered_functions",
            "candidate_covered_functions",
            "semantic_label",
            "component_group",
            "why_hard",
            "manual_notes",
        ]

        # -------------------------
        # Fresh auto-generated base
        # -------------------------
        base_rows: List[Dict[str, object]] = []
        for rid in region_ids:
            info = region_info[int(rid)]
            reps = rep_map.get(int(rid), {})

            base_rows.append(
                {
                    "bench": self.bench,
                    "exe": self.exe,
                    "region_id": int(rid),
                    "is_selected_gap": int(rid in selected_set),
                    "region_coverage": round(float(info.region_coverage), 4),
                    "coverage_class": self._coverage_class(info.region_coverage),
                    "candidate_uncovered_functions": "; ".join(reps.get("uncovered", [])),
                    "candidate_covered_functions": "; ".join(reps.get("covered", [])),
                    "semantic_label": "",
                    "component_group": "",
                    "why_hard": "",
                    "manual_notes": "",
                }
            )

        base = pd.DataFrame(base_rows)

        if base.empty:
            base = pd.DataFrame(columns=id_cols + auto_cols + default_editable_cols)

        # -------------------------
        # If template exists, preserve its editable content
        # -------------------------
        if annot_path.exists():
            prev = pd.read_csv(annot_path)

            # Backward compatibility for older templates
            if "bench" not in prev.columns:
                prev["bench"] = self.bench
            if "exe" not in prev.columns:
                prev["exe"] = self.exe

            if "region_id" in prev.columns:
                prev["region_id"] = pd.to_numeric(prev["region_id"], errors="coerce")
                prev = prev.dropna(subset=["region_id"]).copy()
                prev["region_id"] = prev["region_id"].astype(int)

                # Preserve not only the known editable columns, but also any extra
                # user-added columns in the template.
                prev_extra_cols = [
                    c for c in prev.columns
                    if c not in set(id_cols + auto_cols)
                ]

                editable_cols = []
                for c in default_editable_cols + prev_extra_cols:
                    if c not in editable_cols:
                        editable_cols.append(c)

                # Ensure base has all preserved editable columns
                for col in editable_cols:
                    if col not in base.columns:
                        base[col] = ""

                # Keep only one row per key from the previous template
                prev = prev[id_cols + editable_cols].drop_duplicates(
                    subset=id_cols,
                    keep="last",
                )

                # Merge previous template content back into the fresh base
                base = base.merge(
                    prev,
                    on=id_cols,
                    how="left",
                    suffixes=("", "_tmpl"),
                    indicator=True,
                )

                matched = base["_merge"].eq("both")

                # If a row already exists in the template, use the template values
                # verbatim for editable columns, even if they are blank.
                for col in editable_cols:
                    tmpl_col = f"{col}_tmpl"
                    if tmpl_col in base.columns:
                        base.loc[matched, col] = base.loc[matched, tmpl_col].fillna("")
                        base = base.drop(columns=[tmpl_col])

                base = base.drop(columns=["_merge"])

        # -------------------------
        # Normalize editable text columns
        # -------------------------
        editable_text_cols = [
            c for c in base.columns
            if c not in set(id_cols + auto_cols)
        ]
        for col in editable_text_cols:
            base[col] = base[col].fillna("").astype(str)

        # Stable ordering
        base = base.sort_values(
            ["is_selected_gap", "region_coverage", "region_id"],
            ascending=[False, True, True],
        ).reset_index(drop=True)

        annot_path.parent.mkdir(parents=True, exist_ok=True)
        base.to_csv(annot_path, index=False)
        return base

    def _write_selected_regions_csv(
        self,
        out_path: Path,
        region_info: Dict[int, RegionInfo],
        region_ids: Iterable[int],
        selected_gap_ids: Iterable[int],
        rep_map: Dict[int, Dict[str, List[str]]],
        df_annot: pd.DataFrame,
    ) -> None:
        annot_map = {
            int(r["region_id"]): r for _, r in df_annot.iterrows()
        }
        selected_set = set(int(r) for r in selected_gap_ids)

        rows: List[Dict[str, object]] = []
        for rid in region_ids:
            info = region_info[int(rid)]
            ann = annot_map.get(int(rid), {})
            reps = rep_map.get(int(rid), {})

            rows.append(
                {
                    "bench": self.bench,
                    "exe": self.exe,
                    "region_id": int(rid),
                    "is_selected_gap": int(rid in selected_set),
                    "region_size": int(info.region_size),
                    "covered_nodes": int(info.covered_nodes),
                    "uncovered_nodes": int(info.uncovered_nodes),
                    "region_coverage": round(float(info.region_coverage), 4),
                    "coverage_class": self._coverage_class(info.region_coverage),
                    "semantic_label": ann.get("semantic_label", ""),
                    "component_group": ann.get("component_group", ""),
                    "why_hard": ann.get("why_hard", ""),
                    "uncovered_function_count": len(info.uncovered_function_names),
                    "covered_function_count": len(info.covered_function_names),
                    "rep_uncovered_functions": "; ".join(reps.get("uncovered", [])),
                    "rep_covered_functions": "; ".join(reps.get("covered", [])),
                    "all_uncovered_functions": "; ".join(info.uncovered_function_names),
                    "all_covered_functions": "; ".join(info.covered_function_names),
                }
            )

        out = pd.DataFrame(rows).sort_values(
            ["is_selected_gap", "region_coverage", "region_id"],
            ascending=[False, True, True],
        )
        out.to_csv(out_path, index=False)

    def _write_region_edges_csv(
        self,
        out_path: Path,
        region_graph: nx.DiGraph,
        region_ids: Iterable[int],
    ) -> None:
        rset = set(int(r) for r in region_ids)
        rows: List[Dict[str, object]] = []

        for u, v, d in region_graph.edges(data=True):
            if int(u) not in rset or int(v) not in rset:
                continue
            rows.append(
                {
                    "bench": self.bench,
                    "exe": self.exe,
                    "src_region": int(u),
                    "dst_region": int(v),
                    "edge_weight": int(d.get("weight", 1)),
                }
            )

        pd.DataFrame(rows).sort_values(
            ["edge_weight", "src_region", "dst_region"],
            ascending=[False, True, True],
        ).to_csv(out_path, index=False)

    
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_str_list(v: object) -> List[str]:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return []
        return [x.strip() for x in str(v).split(";") if x.strip()]

    @staticmethod
    def _parse_int_list(v: object) -> List[int]:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return []
        out: List[int] = []
        for x in str(v).split(";"):
            x = x.strip()
            if not x:
                continue
            try:
                out.append(int(x))
            except ValueError:
                continue
        return out

    @staticmethod
    def _coverage_class(rc: float) -> str:
        rc = float(rc)
        if rc == 0.0:
            return "uncovered"
        if rc <= 0.2:
            return "severely_underexplored"
        if rc <= 0.5:
            return "weakly_explored"
        return "well_explored"

    @staticmethod
    def _name_informativeness_score(name: str) -> float:
        bad_tokens = {
            "util", "helper", "common", "wrapper", "impl",
            "internal", "debug", "log", "tmp", "test"
        }
        s = str(name)
        parts = [p.lower() for p in s.replace("::", "_").split("_") if p]

        score = 0.0
        if len(parts) >= 2:
            score += 1.0
        if not any(tok in bad_tokens for tok in parts):
            score += 1.5
        if any(tok in s.lower() for tok in ["parse", "read", "write", "decode", "encode", "check", "load", "open"]):
            score += 1.0
        return score


    # ------------------------------------------------------------------
    # Figure
    # ------------------------------------------------------------------
    def _draw_figure(
        self,
        out_pdf: Path,
        out_png: Path,
        region_graph: nx.DiGraph,
        region_info: Dict[int, RegionInfo],
        region_ids: Iterable[int],
        selected_gap_ids: Iterable[int],
        rep_map: Dict[int, Dict[str, List[str]]],
        df_annot: pd.DataFrame,
    ) -> None:
        import matplotlib.patheffects as pe
        from matplotlib.patches import Patch

        def _clean_text(v: object) -> str:
            if v is None:
                return ""
            if isinstance(v, float) and pd.isna(v):
                return ""
            return str(v).strip()

        def _clip_text(s: object, max_len: int = 70) -> str:
            t = _clean_text(s)
            if len(t) <= max_len:
                return t
            return t[: max_len - 3].rstrip() + "..."

        def _leader_anchor(
            x: float,
            y: float,
            cx: float,
            cy: float,
            node_size: float,
        ) -> Tuple[float, float]:
            dx = x - cx
            dy = y - cy
            norm = math.hypot(dx, dy)
            if norm < 1e-9:
                dx, dy, norm = 1.0, 0.0, 1.0

            offset = 0.08 + 0.015 * math.sqrt(max(1.0, node_size / 1000.0))
            return (x + offset * dx / norm, y + offset * dy / norm)

        rset = {int(r) for r in region_ids}
        selected_set = {int(r) for r in selected_gap_ids}

        sub = region_graph.subgraph(rset).copy()
        if sub.number_of_nodes() == 0:
            raise ValueError("No regions left to draw")

        annot_map = {int(r["region_id"]): r for _, r in df_annot.iterrows()}

        # -------------------------
        # Layout
        # -------------------------
        pos = self._compact_region_layout(
            sub,
            k_scale=1.10,
            outer_shrink=0.40,
            global_scale=0.88,
        )

        fig = plt.figure(figsize=(8.6, 6.8))
        gs = fig.add_gridspec(
            nrows=2,
            ncols=1,
            height_ratios=[4.3, 1.0],
            hspace=0.03,
        )
        ax = fig.add_subplot(gs[0])
        ax_note = fig.add_subplot(gs[1])

        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax_note.set_facecolor("white")
        ax_note.set_xlim(0, 1)
        ax_note.set_ylim(0, 1)
        ax_note.axis("off")

        color_map = {
            "uncovered": "#c93c37",
            "severely_underexplored": "#f39c34",
            "weakly_explored": "#d8c44c",
            "well_explored": "#5ca96b",
        }

        # -------------------------
        # Edges
        # -------------------------
        edges = list(sub.edges(data=True))
        widths = [
            0.6 + 0.35 * math.log2(int(d.get("weight", 1)) + 1)
            for _, _, d in edges
        ]

        nx.draw_networkx_edges(
            sub,
            pos,
            ax=ax,
            arrows=True,
            width=widths,
            alpha=0.14,
            edge_color="#9a9a9a",
            arrowsize=12,
            connectionstyle="arc3,rad=0.04",
        )

        # -------------------------
        # Nodes
        # -------------------------
        node_sizes: Dict[int, float] = {}
        draw_sizes: List[float] = []
        node_colors: List[str] = []
        node_borders: List[str] = []

        for rid in sub.nodes():
            info = region_info[int(rid)]
            size = 900 + 105 * math.sqrt(max(1, int(info.region_size)))
            node_sizes[int(rid)] = size
            draw_sizes.append(size)

            cls = self._coverage_class(info.region_coverage)
            node_colors.append(color_map[cls])
            node_borders.append("#000000" if int(rid) in selected_set else "#7a7a7a")

        nx.draw_networkx_nodes(
            sub,
            pos,
            ax=ax,
            node_size=draw_sizes,
            node_color=node_colors,
            edgecolors=node_borders,
            linewidths=1.8,
            alpha=0.72,
        )

        # -------------------------
        # Outside labels with leader lines
        # -------------------------
        xs = [xy[0] for xy in pos.values()]
        ys = [xy[1] for xy in pos.values()]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        node_ids = [int(r) for r in sub.nodes()]
        label_anchor: Dict[int, List[float]] = {}
        label_pos: Dict[int, List[float]] = {}

        for rid in node_ids:
            x, y = pos[rid]
            lx, ly = _leader_anchor(x, y, cx, cy, node_sizes[rid])
            label_anchor[rid] = [lx, ly]
            label_pos[rid] = [lx, ly]

        min_dx = 0.10
        min_dy = 0.06

        for _ in range(120):
            moved = False
            for i in range(len(node_ids)):
                u = node_ids[i]
                for j in range(i + 1, len(node_ids)):
                    v = node_ids[j]

                    xu, yu = label_pos[u]
                    xv, yv = label_pos[v]

                    dx = xu - xv
                    dy = yu - yv

                    overlap_x = min_dx - abs(dx)
                    overlap_y = min_dy - abs(dy)

                    if overlap_x > 0 and overlap_y > 0:
                        sx = 1.0 if dx >= 0 else -1.0
                        sy = 1.0 if dy >= 0 else -1.0

                        label_pos[u][0] += 0.5 * overlap_x * sx
                        label_pos[v][0] -= 0.5 * overlap_x * sx
                        label_pos[u][1] += 0.5 * overlap_y * sy
                        label_pos[v][1] -= 0.5 * overlap_y * sy
                        moved = True

            for rid in node_ids:
                ax0, ay0 = label_anchor[rid]
                lx, ly = label_pos[rid]
                label_pos[rid][0] = 0.93 * lx + 0.07 * ax0
                label_pos[rid][1] = 0.93 * ly + 0.07 * ay0

            if not moved:
                break

        for rid in node_ids:
            x, y = pos[rid]
            lx, ly = label_pos[rid]

            ax.plot(
                [x, lx],
                [y, ly],
                color="#5f5f5f",
                linewidth=0.8,
                alpha=0.80,
                zorder=6,
            )

            ax.text(
                lx,
                ly,
                f"R{rid}",
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="black",
                zorder=7,
                bbox=dict(
                    boxstyle="round,pad=0.14",
                    facecolor="white",
                    edgecolor="#8a8a8a",
                    linewidth=0.6,
                    alpha=0.96,
                ),
                path_effects=[pe.withStroke(linewidth=1.2, foreground="white")],
            )

        # -------------------------
        # Legend
        # -------------------------
        self._draw_top_header(
            fig,
            color_map=color_map,
            title="",
        )
        ax.axis("off")

        # -------------------------
        # Compact bottom notes
        # Only show selected gaps + a few most important low-coverage regions
        # -------------------------
        ordered = sorted(
            [int(r) for r in sub.nodes()],
            key=lambda rid: (
                0 if rid in selected_set else 1,
                region_info[rid].region_coverage,
                rid,
            ),
        )

        compact_note_ids: List[int] = []
        for rid in ordered:
            if rid in selected_set:
                compact_note_ids.append(rid)

        for rid in ordered:
            if rid not in compact_note_ids:
                compact_note_ids.append(rid)
            if len(compact_note_ids) >= min(8, len(ordered)):
                break

        note_rows: List[Tuple[int, str]] = []
        for rid in compact_note_ids:
            info = region_info[rid]
            ann = annot_map.get(rid, {})
            reps = rep_map.get(rid, {})

            semantic_label = _clean_text(ann.get("semantic_label", ""))
            why_hard = _clean_text(ann.get("why_hard", ""))
            cand_uncov = _clean_text(ann.get("candidate_uncovered_functions", ""))
            cand_cov = _clean_text(ann.get("candidate_covered_functions", ""))

            if not cand_uncov:
                cand_uncov = "; ".join(reps.get("uncovered", []))
            if not cand_cov:
                cand_cov = "; ".join(reps.get("covered", []))

            line = f"R{rid}: rc={info.region_coverage:.2f}, uncovered={info.uncovered_nodes}/{info.region_size}"
            if semantic_label:
                line += f", {semantic_label}"
            elif why_hard:
                line += f", {_clip_text(why_hard, 28)}"
            elif cand_uncov:
                line += f", U={_clip_text(cand_uncov, 22)}"
            elif cand_cov:
                line += f", C={_clip_text(cand_cov, 22)}"

            note_rows.append((rid, _clip_text(line, 95)))

        split = (len(note_rows) + 1) // 2
        left_rows = note_rows[:split]
        right_rows = note_rows[split:]

        max_rows = max(len(left_rows), len(right_rows), 1)
        row_gap = min(0.24, 0.88 / max_rows)

        def _draw_note_column(items: List[Tuple[int, str]], x0: float) -> None:
            y = 0.94
            for rid, line in items:
                cls = self._coverage_class(region_info[rid].region_coverage)
                ax_note.text(
                    x0,
                    y,
                    "■",
                    color=color_map[cls],
                    fontsize=10,
                    ha="left",
                    va="top",
                )
                ax_note.text(
                    x0 + 0.03,
                    y,
                    line,
                    fontsize=10,
                    ha="left",
                    va="top",
                    color="#222222",
                )
                y -= row_gap

        _draw_note_column(left_rows, 0.02)
        _draw_note_column(right_rows, 0.52)

        fig.savefig(out_pdf, bbox_inches="tight")
        fig.savefig(out_png, dpi=240, bbox_inches="tight")
        plt.close(fig)


    def _compact_region_layout(
        self,
        sub: nx.Graph,
        *,
        k_scale: float = 1.25,
        iterations: int = 300,
        outer_quantile: float = 0.70,
        outer_shrink: float = 0.52,
        global_scale: float = 0.92,
    ) -> Dict[int, Tuple[float, float]]:
        """
        Build a compact spring layout and pull far-out nodes
        (such as R11 / R12) closer to the main cluster.

        Parameters
        ----------
        sub : nx.Graph
            Region subgraph to draw.
        k_scale : float
            Base spring-layout spacing. Smaller => tighter packing.
        iterations : int
            Number of spring iterations.
        outer_quantile : float
            Only nodes beyond this radius quantile are compressed.
        outer_shrink : float
            Compression strength for outliers. Smaller => stronger pull inward.
        global_scale : float
            Final overall scale. Smaller => more compact figure.
        """
        pos = nx.spring_layout(
            sub,
            seed=self.layout_seed,
            k=k_scale / max(1, math.sqrt(sub.number_of_nodes())),
            iterations=iterations,
            weight="weight",
        )

        if not pos:
            return pos

        xs = [xy[0] for xy in pos.values()]
        ys = [xy[1] for xy in pos.values()]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)

        radii = {
            rid: math.hypot(pos[rid][0] - cx, pos[rid][1] - cy)
            for rid in pos
        }

        if radii:
            rvals = sorted(radii.values())
            idx = int(outer_quantile * (len(rvals) - 1))
            r_thr = rvals[idx]

            for rid in pos:
                x, y = pos[rid]
                dx = x - cx
                dy = y - cy
                r = math.hypot(dx, dy)

                if r > 1e-9 and r > r_thr:
                    new_r = r_thr + outer_shrink * (r - r_thr)
                    scale = new_r / r
                    pos[rid] = (cx + dx * scale, cy + dy * scale)

        for rid in pos:
            x, y = pos[rid]
            pos[rid] = (global_scale * x, global_scale * y)

        return pos

    def _draw_top_header(
        self,
        fig: plt.Figure,
        *,
        color_map: Dict[str, str],
        title: str,
        top: float = 0.92,
        title_y: float = 0.975,
        label_x: float = 0.06,
        label_y: float = 0.935,
        legend_x: float = 0.19,
        legend_y: float = 0.943,
    ) -> None:
        """
        Draw a compact figure-level header:
        - centered title at the very top
        - one-line coverage legend below it
        """
        from matplotlib.patches import Patch

        fig.subplots_adjust(top=top)

        fig.suptitle(
            title,
            fontsize=10,
            fontweight="bold",
            y=title_y,
        )

        legend_handles = [
            Patch(
                facecolor=color_map["uncovered"],
                edgecolor=color_map["uncovered"],
                label="rc = 0",
            ),
            Patch(
                facecolor=color_map["severely_underexplored"],
                edgecolor=color_map["severely_underexplored"],
                label="0 < rc ≤ 0.2",
            ),
            Patch(
                facecolor=color_map["weakly_explored"],
                edgecolor=color_map["weakly_explored"],
                label="0.2 < rc ≤ 0.5",
            ),
            Patch(
                facecolor=color_map["well_explored"],
                edgecolor=color_map["well_explored"],
                label="rc > 0.5",
            ),
        ]

        legend = ""#"Coverage class"
        fig.text(
            label_x,
            label_y,
            legend,
            ha="left",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="black",
        )

        fig.legend(
            handles=legend_handles,
            loc="upper left",
            bbox_to_anchor=(legend_x, legend_y),
            ncol=4,
            frameon=False,
            fontsize=10.0,
            handlelength=0.8,
            handleheight=0.8,
            handletextpad=0.35,
            columnspacing=1.2,
            borderaxespad=0.0,
        )