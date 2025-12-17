import argparse
from pathlib import Path
from typing import List, Optional, Dict, Any

from .profiles import save_profile, list_profile_paths
from .ossfuzz_scan import CProjectDiscoverer  
from .repo_analyze import ProfileAugmenter, ProfileAugmentWorker, AugmentTaskDistributer    
from .summary import ProfilesSummary          


# ----------------------------------------------------------------------
# CLI commands
# ----------------------------------------------------------------------
def _load_project_list(path: Optional[Path]) -> Optional[List[str]]:
    if path is None:
        return None
    if not path.exists():
        raise SystemExit(f"Project list file not found: {path}")
    names: List[str] = []
    for line in path.read_text().splitlines():
        name = line.strip()
        if name:
            names.append(name)
    return names


def cmd_generate(args: argparse.Namespace) -> None:
    root = args.root.resolve()
    profiles_dir = args.profiles_dir.resolve()
    project_list = _load_project_list(args.project_list)

    discoverer = CProjectDiscoverer(
        oss_fuzz_root=root,
        project_whitelist=project_list,
    )
    profiles = discoverer.discover()

    profiles_dir.mkdir(parents=True, exist_ok=True)
    for p in profiles:
        out_path = profiles_dir / f"{p.project}.yaml"
        save_profile(p, out_path)
        print(f"[generate] wrote {out_path}")

    print(f"[generate] total profiles: {len(profiles)}")


def cmd_augment(args: argparse.Namespace) -> None:
    profiles_dir = args.profiles_dir.resolve()
    clone_root = args.clone_root.resolve()
    jobs = args.jobs

    paths = list_profile_paths(profiles_dir)
    if not paths:
        print(f"[augment] no profiles found in {profiles_dir}")
        return

    paths = sorted(paths)  # deterministic ordering

    print(
        f"[augment] augmenting {len(paths)} profiles with {jobs} "
        f"parallel worker(s)…"
    )

    dist = AugmentTaskDistributer(
        task_name="augment-profiles",
        paths=paths,
        clone_root=clone_root,
        task_num=jobs,
    )
    dist.Distributer()

    summary_path = profiles_dir / "summary.yaml"
    summary = ProfilesSummary(profiles_dir).write(summary_path)
    print(f"[augment] summary written to {summary_path}")

    # Data size overview
    print("[augment] benchmark data size:")
    print(f"  total_projects: {summary['total_projects']}")
    print(f"  loc_total:      {summary['loc_total']}")
    print(f"  loc_min:        {summary['loc_min']}")
    print(f"  loc_max:        {summary['loc_max']}")
    print(
        f"  loc_avg:        {summary['loc_avg']:.2f}"
        if summary['loc_avg'] is not None
        else "  loc_avg:        None"
    )

    # Show top-N largest projects by LOC (flatten from known_domain_projects)
    projects_by_loc: List[Dict[str, Any]] = []
    for domain, plist in summary.get("known_domain_projects", {}).items():
        for entry in plist:
            projects_by_loc.append(
                {
                    "project": entry["project"],
                    "loc": entry["loc"],
                    "domain": domain,
                }
            )

    projects_by_loc.sort(
        key=lambda e: e["loc"] if isinstance(e.get("loc"), int) else -1,
        reverse=True,
    )

    top_n = min(10, len(projects_by_loc))
    if top_n > 0:
        print(f"  top {top_n} projects by LOC:")
        for entry in projects_by_loc[:top_n]:
            print(
                f"    {entry['project']}: "
                f"loc={entry['loc']}, domain={entry['domain']}"
            )


def cmd_summary(args: argparse.Namespace) -> None:
    profiles_dir = args.profiles_dir.resolve()
    summary_path = args.output.resolve()

    summary = ProfilesSummary(profiles_dir).write(summary_path)

    print(f"[summary] written to {summary_path}")

    print("[summary] benchmark data size:")
    print(f"  total_projects: {summary['total_projects']}")
    print(f"  loc_total:      {summary['loc_total']}")
    print(f"  loc_min:        {summary['loc_min']}")
    print(f"  loc_max:        {summary['loc_max']}")
    print(
        f"  loc_avg:        {summary['loc_avg']:.2f}"
        if summary["loc_avg"] is not None
        else "  loc_avg:        None"
    )
    if "min_loc_threshold" in summary:
        print(f"  min_loc_filter: {summary['min_loc_threshold']}")

    print("[summary] domains (count + loc range):")
    # domains dict: domain -> count
    # known_domain_projects dict: domain -> {count, loc_min, loc_max, projects}
    known = summary.get("known_domain_projects", {}) or {}

    # print known domains first, then unknown (if present)
    doms = list(summary.get("domains", {}).items())
    doms.sort(key=lambda kv: kv[0])

    for dom, count in doms:
        if dom == "unknown":
            print(f"  {dom}: {count}")
            continue

        info = known.get(dom, {})
        dmin = info.get("loc_min")
        dmax = info.get("loc_max")
        if dmin is None or dmax is None:
            print(f"  {dom}: {count}, loc_range=None")
        else:
            print(f"  {dom}: {count}, loc_range=[{dmin}, {dmax}]")

    # Global projects-by-LOC view (flatten from known_domain_projects[domain]['projects'])
    projects_by_loc: List[Dict[str, Any]] = []
    for domain, info in known.items():
        for entry in info.get("projects", []) or []:
            projects_by_loc.append(
                {
                    "project": entry.get("project"),
                    "loc": entry.get("loc"),
                    "domain": domain,
                }
            )

    projects_by_loc.sort(
        key=lambda e: e["loc"] if isinstance(e.get("loc"), int) else -1,
        reverse=True,
    )

    if projects_by_loc:
        print("[summary] projects ordered by LOC (desc):")
        for entry in projects_by_loc:
            print(
                f"  {entry['project']}: "
                f"loc={entry['loc']}, domain={entry['domain']}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ossbench",
        description="Benchmark collector for OSS-Fuzz C projects",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Path to oss-fuzz root (default: current directory).",
    )
    parser.add_argument(
        "--profiles-dir",
        type=Path,
        default=Path("profiles"),
        help="Directory with per-project profiles (default: profiles/).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = subparsers.add_parser(
        "generate", help="Generate initial profiles from oss-fuzz."
    )
    p_gen.add_argument(
        "--project-list",
        type=Path,
        default=None,
        help="Optional file with project names (one per line).",
    )
    p_gen.set_defaults(func=cmd_generate)

    # augment
    p_aug = subparsers.add_parser(
        "augment", help="Clone repos, compute LOC, update profiles, and summarize."
    )
    p_aug.add_argument(
        "--clone-root",
        type=Path,
        default=Path("bench_repos"),
        help="Root directory where upstream repos are cloned (default: bench_repos/).",
    )
    p_aug.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=4,
        help="Number of parallel worker processes (default: 4).",
    )
    p_aug.set_defaults(func=cmd_augment)

    # summary
    p_sum = subparsers.add_parser(
        "summary", help="Compute and write overall summary from existing profiles."
    )
    p_sum.add_argument(
        "--output",
        type=Path,
        default=Path("profiles/summary.yaml"),
        help="Summary output path (default: profiles/summary.yaml).",
    )
    p_sum.set_defaults(func=cmd_summary)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
