#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="cppcheck-src"
Action="${1:-build}"
executables=("cppcheck")

# load library
source ../__scripts__/base.sh

initialize() {
  export PATH=/usr/local/bin:$PATH

  if [ ! -d "$target" ]; then
    echo "[cppcheck] cloning upstream repo..."
    git clone --depth 1 https://github.com/danmar/cppcheck.git "$target"
  fi
}


wllvm_compile() {
  export LLVM_COMPILER=clang
  export CC="wllvm"
  export CXX="wllvm++"

  export CFLAGS="-g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
  export CXXFLAGS="$CFLAGS"
  export LDFLAGS=""

  build_dir="build-wllvm"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    cmake "../$target" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DBUILD_GUI=OFF \
      -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON \
      -DENABLE_PCH=OFF \
      -DUSE_BUNDLED_TINYXML2=ON \
      -DUSE_BUNDLED_PCRE=ON \
      -DCMAKE_C_COMPILER="$CC" \
      -DCMAKE_CXX_COMPILER="$CXX" \
      -DCMAKE_C_FLAGS="$CFLAGS" \
      -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
      -DCMAKE_EXE_LINKER_FLAGS="$LDFLAGS"

    make -j"$(nproc)"
  )

  handle_executable "$build_dir/bin" "${executables[@]}"
}



hfuzz_compile() {
  export CC="hfuzz-clang"
  export CXX="hfuzz-clang++"
  export CFLAGS="-g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXXFLAGS="-g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export LDFLAGS=""
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  build_dir="build-hfuzz"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    cmake "../$target" \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DBUILD_GUI=OFF \
      -DCMAKE_DISABLE_PRECOMPILE_HEADERS=ON \
      -DENABLE_PCH=OFF \
      -DUSE_BUNDLED_TINYXML2=ON \
      -DUSE_BUNDLED_PCRE=ON \
      -DCMAKE_C_COMPILER="$CC" \
      -DCMAKE_CXX_COMPILER="$CXX" \
      -DCMAKE_C_FLAGS="$CFLAGS" \
      -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
      -DCMAKE_EXE_LINKER_FLAGS="$LDFLAGS"
    make -j"$(nproc)"
  )

  copy_executable "$build_dir" "${executables[@]}"
}

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

initialize
cd "$ROOT"
compile

