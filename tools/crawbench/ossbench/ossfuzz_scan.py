from pathlib import Path
from typing import List, Optional

from .profiles import ProjectProfile


def _looks_like_c_project(proj_dir: Path) -> bool:
    """
    Heuristic:
      - If build.sh or Dockerfile mention .c files in a compile command.
      - Or there are any .c files inside the project directory.
    """
    texts: List[str] = []

    build_sh = proj_dir / "build.sh"
    dockerfile = proj_dir / "Dockerfile"

    for f in (build_sh, dockerfile):
        if f.exists():
            try:
                texts.append(f.read_text(errors="ignore"))
            except Exception:
                pass

    text = "\n".join(texts)

    c_markers = [
        ".c ",
        ".c\\\n",
        ".c\"",
        ".c'",
        ".c)",
        ".c;",
    ]
    compiler_markers = ["clang ", "clang\n", "gcc ", "gcc\n", "$CC ", "$CC\n"]

    has_c_in_build = any(m in text for m in c_markers) and any(
        cc in text for cc in compiler_markers
    )

    has_local_c = any(p.suffix == ".c" for p in proj_dir.rglob("*.c"))

    return has_c_in_build or has_local_c


def _extract_field_from_project_yaml(yaml_path: Path, field: str) -> Optional[str]:
    """
    Minimal parser for project.yaml: lines like 'field: value'.
    Good enough for 'main_repo', 'primary_repo', and 'language'.
    """
    if not yaml_path.exists():
        return None

    try:
        for line in yaml_path.read_text(errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith(field + ":"):
                _, val = stripped.split(":", 1)
                return val.strip().strip("'\"")
    except Exception:
        return None

    return None


def discover_c_projects(
    oss_fuzz_root: Path, project_whitelist: Optional[List[str]] = None
) -> List[ProjectProfile]:
    """
    Scan oss-fuzz 'projects/' and build initial ProjectProfile objects
    for C-style projects.
    """
    projects_dir = oss_fuzz_root / "projects"
    if not projects_dir.is_dir():
        raise RuntimeError(f"Cannot find 'projects' directory under {oss_fuzz_root}")

    profiles: List[ProjectProfile] = []

    for proj_dir in sorted(projects_dir.iterdir()):
        if not proj_dir.is_dir():
            continue

        proj_name = proj_dir.name

        if project_whitelist is not None and proj_name not in project_whitelist:
            continue

        if not _looks_like_c_project(proj_dir):
            continue

        proj_yaml = proj_dir / "project.yaml"
        if not proj_yaml.exists():
            # some projects might not have project.yaml; skip
            continue

        main_repo = (
            _extract_field_from_project_yaml(proj_yaml, "main_repo")
            or _extract_field_from_project_yaml(proj_yaml, "primary_repo")
        )
        language = _extract_field_from_project_yaml(proj_yaml, "language")

        profile = ProjectProfile(
            project=proj_name,
            oss_fuzz_project_dir=str(proj_dir.relative_to(oss_fuzz_root)),
            main_repo=main_repo,
            language=language,
            domain="",   # present but empty
            loc=None,    # present but empty
        )
        profiles.append(profile)

    return profiles

