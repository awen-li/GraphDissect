from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


BENCHMARK_EXECUTABLES: Dict[str, Dict[str, List[str]]] = {
    "network_and_protocols": {
        "snort3": ["snort", "snort2lua"],
        "unbound": ["unbound-checkconf"],
        "http-parser": ["parsertrace", "url_parser"],
    },
    "media_processing": {
        "ffmpeg": ["ffmpeg", "ffprobe"],
        "libtiff": ["tiff2bw", "tiffinfo", "tiff2pdf"],
        "wavpack": ["wavpack", "wvunpack", "wvgain"],
    },
    "metadata_and_system_utilities": {
        "git": ["git"],
        "sleuthkit": ["istat", "img_stat", "tsk_recover"],
        "file": ["file"],
    },
    "parsing_and_document_processing": {
        "xpdf": ["pdfdetach", "pdfinfo", "pdftops"],
        "libxml2": ["xmllint"],
        "jq": ["jq"],
    },
    "toolchain_and_binary_utilities": {
        "binutils": ["objdump", "readelf", "addr2line"],
        "cppcheck": ["cppcheck"],
        "libdwarf": ["dwarfdump"],
    },
    "language_runtimes_and_interpreters": {
        "cpython3": ["python"],
        "quickjs": ["qjs", "qjsc"],
        "lua": ["lua"],
    },
    "archive_and_compression": {
        "libarchive": ["bsdtar", "bsdcpio"],
        "upx": ["upx"],
        "xz": ["xz"],
    },
    "database_and_storage": {
        "hdf5": ["h5dump", "h5stat", "h5repack"],
        "netcdf": ["ncdump", "ncgen", "ncinfo"],
        "sqlite3": ["sqlite3"],
    },
}


@dataclass(frozen=True)
class Bench:
    name: str
    executables: Tuple[str, ...]              # immutable
    root_dir: Optional[Path] = None
    meta: Dict[str, str] = field(default_factory=dict)

    def exe_paths(self) -> List[Path]:
        if self.root_dir is None:
            return [Path(x) for x in self.executables]
        return [self.root_dir / x for x in self.executables]


@dataclass
class Domain:
    name: str
    benches: Dict[str, Bench] = field(default_factory=dict)

    def add_bench(self, bench: Bench) -> None:
        self.benches[bench.name] = bench

    def iter_benches(self) -> Iterable[Bench]:
        for k in sorted(self.benches.keys()):
            yield self.benches[k]

    def get_bench(self, name: str) -> Bench:
        return self.benches[name]


@dataclass
class Suite:
    domains: Dict[str, Domain] = field(default_factory=dict)

    def add_domain(self, dom: Domain) -> None:
        self.domains[dom.name] = dom

    def get_domain(self, name: str) -> Domain:
        return self.domains[name]

    def iter_domains(self) -> Iterable[Domain]:
        for k in sorted(self.domains.keys()):
            yield self.domains[k]

    def iter_benches(self) -> Iterable[Bench]:
        for dom in self.iter_domains():
            yield from dom.iter_benches()

    def get_bench(self, bench_name: str) -> Bench:
        for dom in self.domains.values():
            if bench_name in dom.benches:
                return dom.benches[bench_name]
        raise KeyError(f"bench not found: {bench_name}")

    def flatten(self) -> List[Tuple[str, str, str]]:
        """Return list of (domain, bench, executable)."""
        out: List[Tuple[str, str, str]] = []
        for dom in self.iter_domains():
            for b in dom.iter_benches():
                for exe in b.executables:
                    out.append((dom.name, b.name, exe))
        return out

    def num_benches(self) -> int:
        return sum(len(dom.benches) for dom in self.domains.values())

    def num_executables(self) -> int:
        return sum(len(b.executables) for b in self.iter_benches())

    @classmethod
    def build_suite(
        cls,
        mapping: Optional[Dict[str, Dict[str, List[str]]]] = None,
        root: Optional[Path] = None,
    ) -> "Suite":
        """
        Build Suite from mapping[domain_name][bench_name] = [exe1, exe2, ...].
        If `root` is provided, Bench.root_dir = root/bench_name.
        """
        if mapping is None:
            mapping = BENCHMARK_EXECUTABLES

        suite = cls()
        for domain_name, benches in mapping.items():
            dom = Domain(name=domain_name)
            for bench_name, exes in benches.items():
                b_root = (root / bench_name) if root else None
                dom.add_bench(
                    Bench(
                        name=bench_name,
                        executables=tuple(exes),
                        root_dir=b_root,
                    )
                )
            suite.add_domain(dom)
        return suite
