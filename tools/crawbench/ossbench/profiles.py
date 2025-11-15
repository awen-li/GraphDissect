from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Iterator, Any, List

import yaml


@dataclass
class ProjectProfile:
    """
    Representation of a single benchmark project.

    domain and loc are present from the beginning:
      - domain: "" (empty string)
      - loc: None
    and will be populated later by augment phase.
    """
    project: str
    oss_fuzz_project_dir: str
    main_repo: Optional[str] = None
    language: Optional[str] = None
    domain: str = ""
    loc: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectProfile":
        return cls(
            project=data.get("project", ""),
            oss_fuzz_project_dir=data.get("oss_fuzz_project_dir", ""),
            main_repo=data.get("main_repo"),
            language=data.get("language"),
            domain=data.get("domain") or "",
            loc=data.get("loc"),
        )


def save_profile(profile: ProjectProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(profile.to_dict(), f, sort_keys=False)


def load_profile(path: Path) -> ProjectProfile:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return ProjectProfile.from_dict(data)


def iter_profiles(profiles_dir: Path) -> Iterator[ProjectProfile]:
    """
    Iterate over all *.yaml profiles in a directory.
    """
    for ypath in sorted(profiles_dir.glob("*.yaml")):
        if not ypath.is_file():
            continue
        yield load_profile(ypath)


def list_profile_paths(profiles_dir: Path) -> List[Path]:
    return sorted(p for p in profiles_dir.glob("*.yaml") if p.is_file())

