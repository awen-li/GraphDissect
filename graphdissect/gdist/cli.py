from __future__ import annotations

import argparse
from pathlib import Path

from gdist.analyzers.analyzer import AnalysisContext
from gdist import analyzers 
from gdist.registry import all_analyzers, select


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gdist")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List analyzers")

    a = sub.add_parser("analyze", help="Run analyzers on a results directory")
    a.add_argument("--results", type=Path, required=True)
    a.add_argument("--drivers", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a.add_argument("--only", type=str, default="", help="Comma-separated analyzer keys (rq1,rq3,...)")
    a.add_argument("--coverage-kind", choices=["edge", "func"], default="edge")
    a.add_argument("--time-slice", type=int, default=300)

    return p


def cmd_list() -> int:
    for an in all_analyzers():
        print(f"{an.key}\t{an.description}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    ctx = AnalysisContext(
        results_dir=args.results,
        out_dir=args.out,
        coverage_kind=args.coverage_kind,
        time_slice_sec=args.time_slice,
    )
    #ctx.drivers = load_drivers(args.drivers)

    keys = [x.strip() for x in args.only.split(",") if x.strip()]
    todo = select(keys) if keys else all_analyzers()

    for an in todo:
        an.run(ctx)

    return 0


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "analyze":
        return cmd_analyze(args)
    raise SystemExit("unknown command")
