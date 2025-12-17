import json
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

import yaml
from .profiles import ProjectProfile, iter_profiles
from .task_distributer import TaskDistributer


DOMAINS_YAML = Path(__file__).with_name("domains.yml")

# Only C / C++ source + headers
C_LANG_WHITELIST = {
    "C",
    "C++",
    "C/C++ Header",
}


class DomainMapper:
    """
    Domain inference driven solely by domains.yml.

    Source of truth:
      - domains[*].examples: defines known projects and their coarse domain (domain.id).

    Behavior:
      - If project is in examples: return (domain_id, f"known/{domain_id}")
      - Else: return ("unknown", None)   (strict mode)
        or optionally fall back to existing profile.domain (compat mode).
    """

    def __init__(self, domains_yaml: Path = DOMAINS_YAML) -> None:
        self.domains_yaml = domains_yaml

        self._yaml_cache: Optional[dict] = None
        self._examples_index_cache: Optional[dict] = None  # project(lower) -> domain_id
        self._coarse_map_cache: Optional[dict] = None

    # --- YAML loading ----------------------------------------------------

    def _load_yaml(self) -> dict:
        if self._yaml_cache is not None:
            return self._yaml_cache
        try:
            with self.domains_yaml.open("r") as f:
                self._yaml_cache = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[domain] WARNING: failed to load {self.domains_yaml}: {e}")
            self._yaml_cache = {}
        return self._yaml_cache

    # --- Build examples index -------------------------------------------

    def _build_examples_index(self) -> dict:
        """
        Build project -> coarse domain id index from domains.yml examples.
        """
        data = self._load_yaml()
        domains = data.get("domains", []) or []

        index: dict[str, str] = {}
        for d in domains:
            dom_id = (d.get("id") or "").strip()
            if not dom_id:
                continue

            for ex in (d.get("examples") or []):
                if not ex:
                    continue
                key = str(ex).strip().lower()
                if not key:
                    continue

                if key in index and index[key] != dom_id:
                    print(
                        f"[domain] WARNING: example '{ex}' appears in multiple domains: "
                        f"{index[key]} and {dom_id}. Keeping {index[key]}."
                    )
                    continue
                index[key] = dom_id

        return index

    def lookup_coarse_domain_from_examples(self, project: str) -> Optional[str]:
        if self._examples_index_cache is None:
            self._examples_index_cache = self._build_examples_index()
        return self._examples_index_cache.get(project.lower().strip())

    # --- Coarse map helpers (still useful elsewhere) ---------------------

    def load_coarse_map(self) -> dict:
        if self._coarse_map_cache is not None:
            return self._coarse_map_cache
        data = self._load_yaml()
        self._coarse_map_cache = data.get("coarse_map", {}) or {}
        return self._coarse_map_cache

    def map_fine_to_coarse(self, fine_label: str) -> str:
        """
        Kept for compatibility, but DomainMapper.infer_domain() no longer
        depends on fine labels.
        """
        if not fine_label:
            return "unknown"
        coarse_map = self.load_coarse_map()
        if fine_label in coarse_map:
            return coarse_map[fine_label]
        parts = fine_label.split("/")
        for i in range(len(parts) - 1, 0, -1):
            key = "/".join(parts[:i])
            if key in coarse_map:
                return coarse_map[key]
        prefix = parts[0]
        if prefix in coarse_map:
            return coarse_map[prefix]
        return coarse_map.get("other", "unknown")

    # --- High-level inference -------------------------------------------

    def infer_domain(self, profile: ProjectProfile) -> tuple[str, Optional[str]]:
        """
        STRICT domains.yml-only inference.
        """
        project = (profile.project or "").strip()
        if not project:
            return "unknown", None

        coarse = self.lookup_coarse_domain_from_examples(project)
        if coarse:
            return coarse, f"known/{coarse}"

        # strict mode: unknown if not in domains.yml examples
        return "unknown", None

    # Optional compatibility variant:
    def infer_domain_compat(self, profile: ProjectProfile) -> tuple[str, Optional[str]]:
        """
        If not in examples, fall back to profile.domain if it is already set.
        Useful if you have partial labels in profiles you don't want to drop.
        """
        coarse, fine = self.infer_domain(profile)
        if coarse != "unknown":
            return coarse, fine

        if profile.domain and str(profile.domain).lower() not in ("unknown", "null", ""):
            # Here we treat profile.domain as already a coarse id
            return str(profile.domain), "profile/domain"

        return "unknown", None


_DEFAULT_DOMAIN_MAPPER: Optional[DomainMapper] = None


def _get_default_domain_mapper() -> DomainMapper:
    global _DEFAULT_DOMAIN_MAPPER
    if _DEFAULT_DOMAIN_MAPPER is None:
        _DEFAULT_DOMAIN_MAPPER = DomainMapper(domains_yaml=DOMAINS_YAML)
    return _DEFAULT_DOMAIN_MAPPER


class ProfileAugmenter:
    """
    Handles repository cloning, LOC computation, and profile augmentation.
    """

    def __init__(self, clone_root: Path, domain_mapper: Optional[DomainMapper] = None) -> None:
        self.clone_root = clone_root
        self.domain_mapper = domain_mapper or _get_default_domain_mapper()

    # --- Repo management -------------------------------------------------
    def clone_repo_if_needed(self, main_repo: str, target_dir: Path) -> None:
        if target_dir.is_dir():
            return
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[clone] git clone {main_repo} -> {target_dir}")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", main_repo, str(target_dir)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[clone] WARNING: git clone failed for {main_repo}: {e}")

    # --- LOC computation using cloc -------------------------------------
    def _compute_loc_with_cloc(self, repo_dir: Path) -> Optional[int]:
        """
        Use cloc to compute LOC for C/C++ sources and headers only.
        Returns total LOC (int) or None if cloc fails.
        """
        try:
            proc = subprocess.run(
                [
                    "cloc",
                    "--json",
                    "--include-lang=C,C++,C/C++ Header",
                    ".",
                ],
                cwd=str(repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            data = json.loads(proc.stdout)

            total = 0
            for lang, info in data.items():
                # cloc metadata keys are not dicts; skip those
                if not isinstance(info, dict):
                    continue
                if lang not in C_LANG_WHITELIST:
                    continue
                code = info.get("code")
                if isinstance(code, int):
                    total += code

            return total
        except Exception as e:
            print(f"[loc] cloc failed in {repo_dir}: {e}")
            return None

    def compute_loc(self, repo_dir: Path) -> int:
        """
        Compute C/C++ LOC using cloc only.
        If cloc fails, return 0 (no slow Python fallback).
        """
        loc = self._compute_loc_with_cloc(repo_dir)
        if loc is None:
            return 0
        return loc

    # --- High-level profile augmentation --------------------------------
    def augment(self, profile: ProjectProfile) -> ProjectProfile:
        main_repo = profile.main_repo
        has_repo = bool(main_repo) and str(main_repo).lower() not in ("null", "")

        # --- LOC: only compute if missing or clearly invalid ---
        if has_repo:
            repo_dir = self.clone_root / profile.project
            self.clone_repo_if_needed(profile.main_repo, repo_dir)

            loc_val = profile.loc
            if loc_val is None or (isinstance(loc_val, int) and loc_val <= 0):
                loc_val = self.compute_loc(repo_dir)
        else:
            loc_val = 0
        
        # --- Domain inference (this already respects existing domain) ---
        coarse_domain, fine_label = self.domain_mapper.infer_domain(profile)

        profile.loc = loc_val
        profile.domain = coarse_domain
        if hasattr(profile, "domain_label"):
            profile.domain_label = fine_label

        print(
            f"[augment] {profile.project}: loc={loc_val}, "
            f"domain={coarse_domain}, fine_label={fine_label}"
        )
        return profile


# ----------------------------------------------------------------------
# Backwards-compatible functional API
# ----------------------------------------------------------------------

def load_coarse_map() -> dict:
    return _get_default_domain_mapper().load_coarse_map()


def map_fine_to_coarse(fine_label: str) -> str:
    return _get_default_domain_mapper().map_fine_to_coarse(fine_label)


def guess_fine_label_from_name(project: str) -> Optional[str]:
    return _get_default_domain_mapper().guess_fine_label_from_name(project)


def infer_domain(profile: ProjectProfile) -> tuple[str, Optional[str]]:
    return _get_default_domain_mapper().infer_domain(profile)


def clone_repo_if_needed(main_repo: str, target_dir: Path) -> None:
    augmenter = ProfileAugmenter(clone_root=target_dir.parent, domain_mapper=_get_default_domain_mapper())
    augmenter.clone_repo_if_needed(main_repo, target_dir)


def compute_loc(repo_dir: Path) -> int:
    augmenter = ProfileAugmenter(clone_root=repo_dir, domain_mapper=_get_default_domain_mapper())
    return augmenter.compute_loc(repo_dir)


def augment_profile(
    profile: ProjectProfile,
    clone_root: Path,
) -> ProjectProfile:
    augmenter = ProfileAugmenter(clone_root=clone_root, domain_mapper=_get_default_domain_mapper())
    return augmenter.augment(profile)


class ProfileAugmentWorker:
    """
    Worker object executed in a subprocess.
    It processes a slice of profile paths and augments each profile.
    """

    def __init__(self, paths: List[Path], clone_root: Path) -> None:
        self.paths = paths
        self.clone_root = clone_root

    def StartRun(self) -> None:
        from .profiles import load_profile, save_profile  # import inside process
        augmenter = ProfileAugmenter(clone_root=self.clone_root)

        total = len(self.paths)
        for idx, path in enumerate(self.paths, start=1):
            profile = load_profile(path)
            #if not "tensorflow" in profile.project.lower():
            #    continue
            print(f"[worker] {path.name} ({idx}/{total})")
            profile = augmenter.augment(profile)
            save_profile(profile, path)


class AugmentTaskDistributer(TaskDistributer):
    """
    TaskDistributer specialization for profile augmentation.
    Splits the list of profile paths into ranges and spawns workers.
    """

    def __init__(
        self,
        task_name: str,
        paths: List[Path],
        clone_root: Path,
        task_num: int = 4,
    ) -> None:
        super().__init__(task_name, ItemSize=len(paths), TaskNum=task_num)
        self.paths = paths
        self.clone_root = clone_root

    def InitObject(self, StartNo: int, EndNo: int) -> ProfileAugmentWorker:
        # EndNo is inclusive in your TaskDistributer
        slice_paths = self.paths[StartNo : EndNo + 1]
        return ProfileAugmentWorker(slice_paths, self.clone_root)

    def Final(self) -> None:
        # Called once after all tasks join
        print("[augment] all worker processes finished.")

