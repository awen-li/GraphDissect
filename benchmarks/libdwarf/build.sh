#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="libdwarf-src"
Action="${1:-}"

# main CLI(s) we care about for driver-based fuzzing
executables=("dwarfdump")

# load shared helpers (your framework)
source ../__scripts__/base.sh

initialize() {
  export PATH=/usr/local/bin:$PATH

  if [ ! -d "$target" ]; then
    echo "[libdwarf] cloning upstream repo..."
    git clone --depth 1 https://github.com/davea42/libdwarf-code "$target"
  fi
}

# -------- WLLVM build (bitcode) --------
wllvm_compile() {
  export LLVM_COMPILER=clang

  export CC="wllvm -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
  export CXX="wllvm++ -g -O2 -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

  # Some autotools/libtool projects mis-handle wrapper link steps; if you hit
  # objcopy-on-script issues, uncomment the next two lines.
  # export CCLD="clang"
  # export CXXLD="clang++"

  # Clean source tree if configured previously
  if [ -d "$target" ]; then
    ( cd "$target" && make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true )
  fi

  build_dir="build-wllvm"
  rm -rf "$build_dir" && mkdir -p "$build_dir"

  (
    cd "$build_dir"
    # libdwarf-code usually provides configure; if not, it provides autogen/bootstrap.
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

  # libdwarf tools are typically under src/bin or similar; handle_executable is robust.
  handle_executable "$build_dir/src/bin/dwarfdump" "${executables[@]}"
}

# -------- Honggfuzz build --------
hfuzz_compile() {
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

  # copy_executable expects directory containing the built binaries; if it misses,
  # switch to "$build_dir/src/bin" etc, or just use handle_executable like above.
  copy_executable "$build_dir" "${executables[@]}"
}

# -------- entrypoints --------
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

