import argparse
from pathlib import Path
from typing import List, Optional

from .profiles import save_profile, iter_profiles, list_profile_paths
from .ossfuzz_scan import discover_c_projects
from .repo_analyze import augment_profile
from .summary import write_summary


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

    profiles = discover_c_projects(root, project_list)

    profiles_dir.mkdir(parents=True, exist_ok=True)
    for p in profiles:
        out_path = profiles_dir / f"{p.project}.yaml"
        save_profile(p, out_path)
        print(f"[generate] wrote {out_path}")

    print(f"[generate] total profiles: {len(profiles)}")


def cmd_augment(args: argparse.Namespace) -> None:
    profiles_dir = args.profiles_dir.resolve()
    clone_root = args.clone_root.resolve()

    paths = list_profile_paths(profiles_dir)
    if not paths:
        print(f"[augment] no profiles found in {profiles_dir}")
        return

    from .profiles import load_profile, save_profile  # local import to avoid cycles

    for path in paths:
        profile = load_profile(path)
        profile = augment_profile(profile, clone_root)
        save_profile(profile, path)

    # After augment, also emit a summary
    summary_path = profiles_dir / "summary.yaml"
    summary = write_summary(profiles_dir, summary_path)

    print(f"[augment] summary written to {summary_path}")

    # Data size overview
    print("[augment] benchmark data size:")
    print(f"  total_projects: {summary['total_projects']}")
    print(f"  loc_total:      {summary['loc_total']}")
    print(f"  loc_min:        {summary['loc_min']}")
    print(f"  loc_max:        {summary['loc_max']}")
    print(f"  loc_avg:        {summary['loc_avg']:.2f}"
          if summary['loc_avg'] is not None else "  loc_avg:        None")

    # Show top-N largest projects by LOC
    projects_by_loc = summary.get("projects_by_loc", [])
    top_n = min(10, len(projects_by_loc))
    if top_n > 0:
        print(f"  top {top_n} projects by LOC:")
        for entry in projects_by_loc[:top_n]:
            print(f"    {entry['project']}: loc={entry['loc']}, domain={entry['domain']}")


def cmd_summary(args: argparse.Namespace) -> None:
    profiles_dir = args.profiles_dir.resolve()
    summary_path = args.output.resolve()
    summary = write_summary(profiles_dir, summary_path)

    print(f"[summary] written to {summary_path}")

    print("[summary] benchmark data size:")
    print(f"  total_projects: {summary['total_projects']}")
    print(f"  loc_total:      {summary['loc_total']}")
    print(f"  loc_min:        {summary['loc_min']}")
    print(f"  loc_max:        {summary['loc_max']}")
    print(f"  loc_avg:        {summary['loc_avg']:.2f}"
          if summary['loc_avg'] is not None else "  loc_avg:        None")

    print("[summary] domains:")
    for dom, count in summary["domains"].items():
        print(f"  {dom}: {count}")

    projects_by_loc = summary.get("projects_by_loc", [])
    if projects_by_loc:
        print("[summary] projects ordered by LOC (desc):")
        for entry in projects_by_loc:
            print(f"  {entry['project']}: loc={entry['loc']}, domain={entry['domain']}")


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

