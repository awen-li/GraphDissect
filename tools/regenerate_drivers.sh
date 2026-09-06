#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/graphdissect/gdriver${PYTHONPATH:+:$PYTHONPATH}"

selected_targets=(
  benchmarks/snort3/snort
  benchmarks/ffmpeg/ffmpeg
  benchmarks/git/git
  benchmarks/xpdf/pdftops
  benchmarks/cppcheck/cppcheck
  benchmarks/cpython3/python
  benchmarks/upx/upx
  benchmarks/hdf5/h5dump
)

usage() {
  echo "Usage: $0 [--selected|--all]"
  echo "  --selected  regenerate drivers for the eight revision subjects (default)"
  echo "  --all       regenerate drivers for every non-baseline executable"
}

mode="${1:---selected}"
case "$mode" in
  --selected)
    targets=("${selected_targets[@]}")
    ;;
  --all)
    mapfile -d '' targets < <(
      find "$REPO_ROOT/benchmarks" \
        -path "$REPO_ROOT/benchmarks/baseline" -prune -o \
        -name cmdspec.yaml -printf '%h\0' | sort -z
    )
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

resolved_targets=()
preflight_failed=0
for target in "${targets[@]}"; do
  if [[ "$target" != /* ]]; then
    target="$REPO_ROOT/$target"
  fi
  resolved_targets+=("$target")
  if [[ ! -f "$target/cmdspec.yaml" ]]; then
    echo "Missing $target/cmdspec.yaml" >&2
    preflight_failed=1
  fi
  executable="$target/$(basename "$target")"
  if [[ ! -x "$executable" ]]; then
    echo "Missing executable $executable" >&2
    preflight_failed=1
  fi
  if [[ ! -d "$target/seeds" ]]; then
    echo "Missing seed directory $target/seeds" >&2
    preflight_failed=1
  fi
done

if (( preflight_failed )); then
  echo "Driver generation aborted; build the targets and extract their seeds first." >&2
  exit 1
fi

for target in "${resolved_targets[@]}"; do
  executable_name="$(basename "$target")"
  executable="$target/$executable_name"
  driver_list="$target/drivers/driver_list.json"
  if [[ ! -f "$driver_list" ]] || ! find "$target/drivers" -mindepth 2 -maxdepth 2 -type f -name '*.json' -print -quit | grep -q .; then
    rm -rf "$target/drivers"
  fi
  echo "Generating drivers: ${target#"$REPO_ROOT/"}"
  python3 -m gdriver "$target"
  while IFS= read -r driver_dir; do
    ln -sfn "../../$executable_name" "$driver_dir/$executable_name"
  done < <(find "$target/drivers" -mindepth 1 -maxdepth 1 -type d -print)
done
