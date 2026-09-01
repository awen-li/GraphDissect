#!/usr/bin/env python3
"""Create deterministic, immutable seed samples and a provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
import shutil


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sizes", type=int, nargs="+", required=True)
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--base-seed", type=int, default=20260416)
    args = parser.parse_args()
    files = sorted(path for path in args.source.rglob("*") if path.is_file())
    if not files:
        raise SystemExit(f"no seed files found under {args.source}")
    invalid = sorted(size for size in args.sizes if size < 1 or size > len(files))
    if invalid:
        raise SystemExit(f"sample sizes outside 1..{len(files)}: {invalid}")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {"source": str(args.source.resolve()), "source_count": len(files), "samples": []}
    for size in sorted(set(args.sizes)):
        for replicate in range(1, args.replicates + 1):
            seed = args.base_seed + size * 1000 + replicate
            selected = sorted(random.Random(seed).sample(files, size))
            sample_dir = args.output / f"n{size}" / f"r{replicate:02d}"
            sample_dir.mkdir(parents=True, exist_ok=False)
            entries = []
            for index, source in enumerate(selected, start=1):
                target = sample_dir / f"{index:05d}_{source.name}"
                shutil.copy2(source, target)
                entries.append({"source": str(source.resolve()), "target": str(target.relative_to(args.output)), "sha256": digest(target)})
            manifest["samples"].append({"size": size, "replicate": replicate, "random_seed": seed, "directory": str(sample_dir.relative_to(args.output)), "files": entries})
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
