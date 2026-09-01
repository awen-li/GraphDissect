#!/usr/bin/env python3
"""Generate deterministic driver subsets for driver-count sensitivity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver-list", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", required=True)
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--base-seed", type=int, default=20260416)
    args = parser.parse_args()
    data = json.loads(args.driver_list.read_text(encoding="utf-8"))
    ids = sorted(int(next(iter(entry))) for entry in data["drivers"])
    invalid = sorted(size for size in args.sizes if size < 1 or size > len(ids))
    if invalid:
        raise SystemExit(f"portfolio sizes outside 1..{len(ids)}: {invalid}")
    portfolios = []
    for size in sorted(set(args.sizes)):
        if size == len(ids):
            portfolios.append({"size": size, "replicate": 1, "random_seed": None, "driver_ids": ids})
            continue
        seen: set[tuple[int, ...]] = set()
        maximum = min(args.replicates, 10000)
        attempt = 0
        while len(seen) < maximum and attempt < maximum * 100:
            attempt += 1
            seed = args.base_seed + size * 100000 + attempt
            portfolio = tuple(sorted(random.Random(seed).sample(ids, size)))
            if portfolio in seen:
                continue
            seen.add(portfolio)
            portfolios.append({"size": size, "replicate": len(seen), "random_seed": seed, "driver_ids": list(portfolio)})
        if len(seen) < maximum:
            print(f"warning: only {len(seen)} unique portfolios exist for size {size}")
    output = {"driver_list": str(args.driver_list.resolve()), "available_driver_ids": ids, "portfolios": portfolios}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
