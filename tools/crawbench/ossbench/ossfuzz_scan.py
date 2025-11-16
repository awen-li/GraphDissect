from pathlib import Path
from typing import List, Optional

from .profiles import ProjectProfile


def _looks_like_c_project(proj_dir: Path) -> bool:
    """
    Heuristic for native (C / C++) projects:
      - If build.sh or Dockerfile mention .c/.cc/.cpp/.cxx files in a compile command.
      - Or there are any .c/.cc/.cpp/.cxx files inside the project directory.
      - Or project.yaml explicitly says language: c / c++ / cpp / c++17 / etc.
    """
    # First, check project.yaml language hint.
    proj_yaml = proj_dir / "project.yaml"
    lang = _extract_field_from_project_yaml(proj_yaml, "language")
    if lang:
        lang_lower = lang.strip().lower()
        if any(k in lang_lower for k in ["c++", "cpp", "c "]) or lang_lower == "c":
            return True

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

    # Extensions we care about for native code
    src_markers = [
        ".c ",
        ".c\\\n",
        ".c\"",
        ".c'",
        ".c)",
        ".c;",
        ".cc ",
        ".cc\\\n",
        ".cc\"",
        ".cc'",
        ".cc)",
        ".cc;",
        ".cpp ",
        ".cpp\\\n",
        ".cpp\"",
        ".cpp'",
        ".cpp)",
        ".cpp;",
        ".cxx ",
        ".cxx\\\n",
        ".cxx\"",
        ".cxx'",
        ".cxx)",
        ".cxx;",
    ]

    # Compiler markers for both C and C++
    compiler_markers = [
        "clang ", "clang\n",
        "clang++ ", "clang++\n",
        "gcc ", "gcc\n",
        "g++ ", "g++\n",
        "$CC ", "$CC\n",
        "$CXX ", "$CXX\n",
    ]

    has_native_in_build = any(m in text for m in src_markers) and any(
        cc in text for cc in compiler_markers
    )

    # Fallback: search for any C/C++ files in the project dir itself
    native_exts = {".c", ".cc", ".cpp", ".cxx"}
    has_local_native = any(p.suffix in native_exts for p in proj_dir.rglob("*"))

    return has_native_in_build or has_local_native


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

