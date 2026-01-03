#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="libdwarf-src"
Action="${1:-}"

# main CLI(s) we care about for driver-based fuzzing
executables=("dwarfdump")

# load shared helpers (your framework)
source ../__scripts__/base.sh

initialize() 
{
  export PATH=/usr/local/bin:$PATH

  if [ ! -d "$target" ]; then
    echo "[libdwarf] cloning upstream repo..."
    git clone --depth 1 https://github.com/davea42/libdwarf-code "$target"
  fi
}


wllvm_compile() 
{
    export LLVM_COMPILER=clang
    export CC="wllvm -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
    export CXX="wllvm++ -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

    if [ -d "$target" ]; then
      ( cd "$target" && make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true )
    fi

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir -p "$build_dir"

    (
      cd "$build_dir"

      if [ ! -x "../$target/configure" ]; then
        echo "[libdwarf] configure missing, attempting to generate..."
        ( cd "../$target" && ./autogen.sh ) || ( cd "../$target" && autoreconf -fi )
      fi

      "../$target/configure" \
        --disable-shared \
        --enable-static \
        --disable-dependency-tracking \
        CFLAGS="-g -O2" \
        CXXFLAGS="-g -O2"

      make -j"$(nproc)"
    )

    handle_executable "$build_dir/src/bin/dwarfdump" "${executables[@]}"
}


hfuzz_compile() 
{
  export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  if [ -d "$target" ]; then
    ( cd "$target" && make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true )
  fi

  build_dir="build-hfuzz"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    if [ ! -x "../$target/configure" ]; then
      echo "[libdwarf] configure missing, attempting to generate..."
      ( cd "../$target" && ./autogen.sh ) || ( cd "../$target" && autoreconf -fi )
    fi

    "../$target/configure" \
      --disable-shared \
      --enable-static \
      --disable-dependency-tracking

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

