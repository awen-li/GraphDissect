from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import csv

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
        "libarchive": ["bsdtar", "bsdunzip"],
        "upx": ["upx"],
        "xz": ["xz"],
    },
    "database_and_storage": {
        "hdf5": ["h5dump", "h5ls", "h5repack"],
        "netcdf": ["ncdump", "ncgen", "nccopy"],
        "sqlite3": ["sqlite3"],
    },
}

@dataclass(frozen=True)
class Bench:
    name: str
    executables: Tuple[str, ...]
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
        for b in self.benches.values():
            yield b

    def get_bench(self, name: str) -> Bench:
        return self.benches[name]


class Suite:
    def __init__(self, suitPath: Path | str):
        self.suitPath = Path(suitPath).absolute()
        self.domains: Dict[str, Domain] = {}
        self.build_suite(mapping=BENCHMARK_EXECUTABLES)

    def add_domain(self, dom: Domain) -> None:
        self.domains[dom.name] = dom

    def get_domain(self, name: str) -> Domain:
        return self.domains[name]

    def iter_domains(self) -> Iterable[Domain]:
        for d in self.domains.values():
            yield d

    def iter_benches(self) -> Iterable[Bench]:
        for dom in self.iter_domains():
            yield from dom.iter_benches()

    def get_bench(self, bench_name: str) -> Bench:
        for dom in self.domains.values():
            if bench_name in dom.benches:
                return dom.benches[bench_name]
        raise KeyError(f"bench not found: {bench_name}")

    def build_suite(
        self,
        mapping: Optional[Dict[str, Dict[str, List[str]]]] = None,
        root: Optional[Path] = None,
    ) -> None:
        """
        Build Suite from mapping[domain_name][bench_name] = [exe1, exe2, ...].
        If `root` is provided, Bench.root_dir = root/bench_name.
        If `root` is None, this Suite's suitPath is used as root.
        """
        if mapping is None:
            raise ValueError("mapping is required (or pass BENCHMARK_EXECUTABLES)")

        if root is None:
            root = self.suitPath

        for domain_name, benches in mapping.items():
            dom = Domain(name=domain_name)
            for bench_name, exes in benches.items():
                b_root = root / bench_name
                dom.add_bench(
                    Bench(
                        name=bench_name,
                        executables=tuple(exes),
                        root_dir=b_root,
                    )
                )
            self.add_domain(dom)

    def show_suite(
        self,
        csv_path: Path | str = "benchinfo.csv",
        warn: bool = True,
    ) -> Path:
        """
        Replicates the shell script behavior:
          <BENCH_ROOT>/<benchmark>/<executable>/faddr_id.map  -> function_count (line count)
          <BENCH_ROOT>/<benchmark>/<executable>/drivers/*/    -> driver_count (immediate child dirs)
        Writes CSV with header:
          benchmark,executable,exe_dir,function_count,driver_count,faddr_id_map_path,drivers_dir_path
        """
        csv_path = self.suitPath / csv_path

        header = [
            "benchmark",
            "executable",
            "exe_dir",
            "function_count",
            "driver_count",
            "faddr_id_map_path",
            "drivers_dir_path",
        ]

        def _count_lines(p: Path) -> int:
            # Fast + robust line count (works for large files)
            n = 0
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    n += chunk.count(b"\n")
            return n

        def _count_immediate_subdirs(p: Path) -> int:
            if not p.is_dir():
                return 0
            return sum(1 for x in p.iterdir() if x.is_dir())

        with csv_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)

            for dom in self.iter_domains():
                for bench in dom.iter_benches():
                    bench_name = bench.name
                    bench_root = bench.root_dir if bench.root_dir is not None else (self.suitPath / bench_name)

                    for exe in bench.executables:
                        exe_dir = bench_root / exe
                        if not exe_dir.is_dir():
                            if warn:
                                print(f"Warning: Executable directory not found: {exe_dir}")
                            continue

                        fid_map_file = exe_dir / "faddr_id.map"
                        if not fid_map_file.is_file():
                            if warn:
                                print(f"Warning: faddr_id.map not found: {fid_map_file}")
                            continue

                        drivers_dir = exe_dir / "drivers"
                        if not drivers_dir.is_dir():
                            if warn:
                                print(f"Warning: Drivers directory not found: {drivers_dir}")
                            continue

                        func_cnt = _count_lines(fid_map_file)
                        drv_cnt = _count_immediate_subdirs(drivers_dir)

                        w.writerow([
                            bench_name,
                            exe,
                            str(exe_dir),
                            func_cnt,
                            drv_cnt,
                            str(fid_map_file),
                            str(drivers_dir),
                        ])

        return csv_path
