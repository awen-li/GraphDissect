#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target=wavpack_src

Action="${1:-compile}"

# CLI executables to use in your pipeline
executables=("wavpack" "wvunpack" "wvgain")

# load library
source ../__scripts__/base.sh

initialize() {
  export PATH=/usr/local/bin:$PATH

  if [[ ! -d "$target" ]]; then
    echo "[wavpack] cloning upstream repo..."
    git clone --depth 1 https://github.com/dbry/WavPack.git "$target"
  fi
}

wllvm_compile() {
  export CC="wllvm -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
  export CXX="wllvm++ -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

  # clean source tree (best-effort)
  if [[ -d "$target" ]]; then
    ( cd "$target" && (make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true) )
  fi

  build_dir="build-wllvm"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  # WavPack repo usually has configure already; if not, try autoreconf.
  if [[ ! -x "$target/configure" && -f "$target/configure.ac" ]]; then
    echo "[wavpack] configure not found, running autoreconf -fi..."
    ( cd "$target" && autoreconf -fi )
  fi

  if [[ ! -x "$target/configure" ]]; then
    echo "[wavpack] ERROR: configure missing in $target"
    exit 1
  fi

  pushd "$build_dir" >/dev/null
  "../$target/configure" \
    --disable-shared \
    --enable-static
  make -j4
  popd >/dev/null

  # Your base.sh likely extracts bitcode + stores it, so keep handle_executable here
  handle_executable "$build_dir/cli" "${executables[@]}"
}

hfuzz_compile() {
  export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  # clean source tree (best-effort)
  if [[ -d "$target" ]]; then
    ( cd "$target" && (make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true) )
  fi

  build_dir="build-hfuzz"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  if [[ ! -x "$target/configure" && -f "$target/configure.ac" ]]; then
    echo "[wavpack] configure not found, running autoreconf -fi..."
    ( cd "$target" && autoreconf -fi )
  fi

  if [[ ! -x "$target/configure" ]]; then
    echo "[wavpack] ERROR: configure missing in $target"
    exit 1
  fi

  pushd "$build_dir" >/dev/null
  "../$target/configure" \
    --disable-shared \
    --enable-static
  make -j4
  popd >/dev/null

  copy_executable "$build_dir/cli" "${executables[@]}"
}

# -------------------------
# actions (same pattern as your libxml2 build.sh)
# -------------------------

if [[ "$Action" == "clean" ]]; then
  exe="${2:-}"
  if [[ -n "$exe" ]]; then
    targets=("$exe")
  else
    targets=("${executables[@]}")
  fi
  clean "${targets[@]}"
  exit 0
fi

if [[ "$Action" == "show" ]]; then
  show_driver_info "${executables[@]}"
  exit 0
fi

cd "$ROOT"
compile
