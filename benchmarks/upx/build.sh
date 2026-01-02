#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="upx-src"
Action="${1:-static}"

executables=("upx")

# load shared helpers (compile/clean/show/handle_executable/copy_executable, etc.)
source ../__scripts__/base.sh

initialize() {
  export PATH=/usr/local/bin:$PATH

  if [ ! -d "$target" ]; then
    echo "[upx] cloning upstream repo..."
    git clone --depth 1 https://github.com/upx/upx.git "$target"
    cd $target && git submodule update --init --recursive  && cd - 
  fi
}

wllvm_compile() {
  export LLVM_COMPILER=clang
  export CC="wllvm -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
  export CXX="wllvm++ -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

  build_dir="build-wllvm"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    cmake "../$target" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    make -j"$(nproc)"
  )

  handle_executable "$build_dir" "${executables[@]}"
}

hfuzz_compile() {
  export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  build_dir="build-hfuzz"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    cmake "../$target" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    make -j"$(nproc)"
  )

  if [ -x "$build_dir/upx" ]; then
    copy_executable "$build_dir" "${executables[@]}"
  elif [ -x "$build_dir/src/upx" ]; then
    copy_executable "$build_dir/src" "${executables[@]}"
  else
    echo "[upx] ERROR: built upx not found under $build_dir"
    find "$build_dir" -maxdepth 3 -type f -name upx -perm -111 -print || true
    exit 1
  fi
}

# ---- dispatch helpers (same pattern as your other benchmarks) ----

if [ "$Action" == "clean" ]; then
  exe="${2:-}"
  if [ -n "$exe" ]; then
    targets=("$exe")
  else
    targets=("${executables[@]}")
  fi
  clean "${targets[@]}"
  exit 0
fi

if [ "$Action" == "show" ]; then
  show_driver_info "${executables[@]}"
  exit 0
fi

cd "$ROOT"
compile

