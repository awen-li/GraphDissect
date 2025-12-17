from pathlib import Path
from typing import Dict, Any, List

import yaml

from .profiles import iter_profiles, ProjectProfile


class ProfilesSummary:
    """
    Compute and optionally persist an overview of project profiles:

      - total_projects
      - per-domain counts
      - LOC stats (total/min/max/avg)
      - known_domain_projects: domain -> [{project, loc}] (sorted by LOC desc)
      - unknown_domain_projects: [project_name, ...]
    """

    def __init__(self, profiles_dir: Path) -> None:
        self.profiles_dir = profiles_dir
        self._profiles: List[ProjectProfile] = []

    # -------- Internal helpers --------
    def _load_profiles(self) -> List[ProjectProfile]:
        if not self._profiles:
            self._profiles = list(iter_profiles(self.profiles_dir))
        return self._profiles

    # -------- Public API --------
    def compute(self) -> Dict[str, Any]:
        profiles = self._load_profiles()

        # Filter out tiny projects (< 2K LOC)
        MIN_LOC = 2000
        filtered: List[ProjectProfile] = []
        for p in profiles:
            loc = p.loc if isinstance(p.loc, int) else None
            if loc is None:
                # keep unknown LOC? (consistent with current behavior)
                filtered.append(p)
                continue
            if loc >= MIN_LOC:
                filtered.append(p)

        profiles = filtered

        total_projects = len(profiles)
        loc_values: List[int] = []
        domain_counts: Dict[str, int] = {}
        domain_to_projects: Dict[str, List[ProjectProfile]] = {}

        for profile in profiles:
            if isinstance(profile.loc, int):
                loc_values.append(profile.loc)

            domain = profile.domain or "unknown"
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            domain_to_projects.setdefault(domain, []).append(profile)

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

        # Known domains: per-domain count + loc stats + projects sorted by LOC desc
        known_domain_projects: Dict[str, Any] = {}

        for domain, plist in domain_to_projects.items():
            if domain == "unknown":
                continue

            # LOC stats inside this domain (ignore missing loc)
            d_locs = [p.loc for p in plist if isinstance(p.loc, int)]
            d_loc_min = min(d_locs) if d_locs else None
            d_loc_max = max(d_locs) if d_locs else None

            # sort inside this domain only, large → small
            sorted_in_domain = sorted(
                plist,
                key=lambda p: p.loc if isinstance(p.loc, int) else -1,
                reverse=True,
            )

            known_domain_projects[domain] = {
                "count": len(plist),
                "loc_min": d_loc_min,
                "loc_max": d_loc_max,
                "projects": [
                    {"project": p.project, "loc": p.loc}
                    for p in sorted_in_domain
                ],
            }

        # Unknown domain: project names (sorted alphabetically for readability)
        unknown_projects = [p.project for p in domain_to_projects.get("unknown", [])]
        unknown_projects.sort()

        summary["known_domain_projects"] = known_domain_projects
        summary["unknown_domain_projects"] = unknown_projects
        summary["min_loc_threshold"] = MIN_LOC

        return summary


    def write(self, output_path: Path) -> Dict[str, Any]:
        """
        Compute and write summary to YAML, return it as a dict.
        """
        summary = self.compute()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(summary, f, sort_keys=False)
        return summary


# -------- Backwards-compatible functional API --------

def compute_summary(profiles_dir: Path) -> Dict[str, Any]:
    """
    Compute an overview (see ProfilesSummary.compute for details).
    """
    return ProfilesSummary(profiles_dir).compute()


def write_summary(profiles_dir: Path, output_path: Path) -> Dict[str, Any]:
    """
    Compute and write summary to YAML, return it as a dict.
    """
    return ProfilesSummary(profiles_dir).write(output_path)
