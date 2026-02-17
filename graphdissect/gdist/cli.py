from __future__ import annotations

import argparse
from pathlib import Path

from gdist.graph.graph import DrvGraph
from gdist.benchs import Suite

from gdist.analyzers.analyzer import AnalysisContext
from gdist import analyzers 
from gdist.analyzers import all_analyzers, select


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gdist")
    sub = p.add_subparsers(dest="cmd", required=True)

    # list command
    sub.add_parser("list", help="List analyzers")

    # show benchs
    s = sub.add_parser("list-benches", help="List benchs")
    s.add_argument("--suite", type=Path, required=True)

    # analyze command
    a = sub.add_parser("analyze", help="Run analyzers on a directory of a bench")
    a.add_argument("--suite", type=Path, required=True)
    a.add_argument("--analyzers", type=str, nargs="+", required=False, help="analyzers to run (default: all)")
    return p


def cmd_list() -> int:
    for an in all_analyzers():
        print(f"{an.key}\t{an.description}")
    return 0


def cmd_list_benches(args: argparse.Namespace) -> int:
    suite = Suite(args.suite)
    spath = suite.show_suite()
    print(f"bench info written to {spath}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    suite = Suite(args.suite)
    suite_root = suite.suitPath

    analyzer_classes: List[Type[Analyzer]] = select(getattr(args, "analyzers", None))
    for dname, domain in suite.domains.items():
        for bname, bench in domain.benches.items():
            for exe in bench.executables:
                bench_dir = (suite_root / bench.name).resolve()
                if not bench_dir.exists():
                    raise FileNotFoundError(f"benchDir not found: {bench_dir}")
                print(f"Analyzing {dname}-{bench.name}-{exe}...")

                ctx = AnalysisContext( benchDir=bench_dir/exe)            
                for an_cls in analyzer_classes:
                    an = an_cls()  # instantiate
                    print(f"  Running analyzer: {an.key} - {an.description}")
                    res = an.run(ctx)
                    print(f"    Done. Generated tables: {list(res.tables.keys())}")

    return 0


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.cmd == "list":
        return cmd_list()

    if args.cmd == "list-benches":
        return cmd_list_benches(args)

    if args.cmd == "analyze":
        return cmd_analyze(args)
    
    raise SystemExit("unknown command")
