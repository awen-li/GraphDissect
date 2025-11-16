from pathlib import Path
from typing import Dict, Any, List

import yaml

from .profiles import iter_profiles, ProjectProfile


def _sorted_projects_by_loc(profiles: List[ProjectProfile]) -> List[Dict[str, Any]]:
    """
    Return a list of dicts {project, loc, domain} sorted by LOC (desc),
    with projects missing loc at the end.
    """
    def sort_key(p: ProjectProfile):
        # None -> -1 so that they go to the end when reversed=False,
        # but we will sort with reverse=True, so: use 0 for None and
        # rely on reverse to push them to the end.
        return p.loc if p.loc is not None else -1

    sorted_profiles = sorted(profiles, key=sort_key, reverse=True)

    result: List[Dict[str, Any]] = []
    for p in sorted_profiles:
        result.append({
            "project": p.project,
            "loc": p.loc,
            "domain": p.domain or "unknown",
        })
    return result


def compute_summary(profiles_dir: Path) -> Dict[str, Any]:
    """
    Compute an overview:
      - total_projects
      - per-domain counts
      - LOC stats (total/min/max/avg)
      - projects_by_loc: list of {project, loc, domain}, sorted by LOC desc
    """
    profiles: List[ProjectProfile] = list(iter_profiles(profiles_dir))

    total_projects = len(profiles)
    loc_values: List[int] = []
    domain_counts: Dict[str, int] = {}

    for profile in profiles:
        if profile.loc is not None:
            loc_values.append(profile.loc)

        domain = profile.domain or "unknown"
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    summary: Dict[str, Any] = {
        "total_projects": total_projects,
        "domains": domain_counts,
    }

    if loc_values:
        summary["loc_total"] = sum(loc_values)
        summary["loc_min"] = min(loc_values)
        summary["loc_max"] = max(loc_values)
        summary["loc_avg"] = sum(loc_values) / len(loc_values)
    else:
        summary["loc_total"] = 0
        summary["loc_min"] = None
        summary["loc_max"] = None
        summary["loc_avg"] = None

    # Add ordered project list
    summary["projects_by_loc"] = _sorted_projects_by_loc(profiles)

    return summary


def write_summary(profiles_dir: Path, output_path: Path) -> Dict[str, Any]:
    """
    Compute and write summary to YAML, return it as a dict.
    """
    summary = compute_summary(profiles_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(summary, f, sort_keys=False)
    return summary
