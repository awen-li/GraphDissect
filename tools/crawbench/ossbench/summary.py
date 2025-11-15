from pathlib import Path
from typing import Dict, Any

import yaml

from .profiles import iter_profiles


def compute_summary(profiles_dir: Path) -> Dict[str, Any]:
    """
    Compute a simple overview: total projects, LOC stats, domain counts.
    """
    total_projects = 0
    loc_values = []
    domain_counts: Dict[str, int] = {}

    for profile in iter_profiles(profiles_dir):
        total_projects += 1

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

