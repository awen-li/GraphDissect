#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="sleuthkit_source"

fs_executables=("fsstat" "blkstat" "istat")
img_executables=("img_stat")
tsk_executables=("tsk_recover" "tsk_imageinfo")

# Flatten for clean/show
executables=(
  "${fs_executables[@]}"
  "${img_executables[@]}"
  "${tsk_executables[@]}"
)

Action="${1:-}"

source ../__scripts__/base.sh

ensure_configure() {
  if [ -f "$target/configure" ]; then
    return
  fi

  if [ -x "$target/bootstrap" ]; then
    (cd "$target" && ./bootstrap)
  elif [ -x "$target/autogen.sh" ]; then
    (cd "$target" && ./autogen.sh)
  else
    (cd "$target" && autoreconf -fi)
  fi

  if [ ! -f "$target/configure" ]; then
    echo "[sleuthkit] ERROR: configure script still missing after bootstrap/autoreconf"
    exit 1
  fi
}

initialize() {
  if [ ! -d "$target" ]; then
    echo "[sleuthkit] cloning upstream repo..."
    git clone --depth 1 https://github.com/sleuthkit/sleuthkit "$target"
  fi
  ensure_configure
}

wllvm_compile() {
  export LLVM_COMPILER=clang
  export CC="wllvm"
  export CXX="wllvm++"

  COMMON_FLAGS="-g -O2 \
    -fno-discard-value-names \
    -fno-inline-functions \
    -mllvm -inline-threshold=0"

  export CFLAGS="${COMMON_FLAGS}"
  export CXXFLAGS="${COMMON_FLAGS} -std=c++17"
  export LDFLAGS="-pg"

  build_dir="build-wllvm"
  rm -rf "$build_dir" && mkdir "$build_dir"

  cd "$build_dir"
  ../"$target"/configure --disable-shared --enable-static \
    CC="$CC" CXX="$CXX" \
    CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" LDFLAGS="$LDFLAGS"

  # Pass CC/CXX to make as well for determinism (same lesson as git)
  make -j"$(nproc)" V=1 \
    CC="$CC" CXX="$CXX" \
    CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" LDFLAGS="$LDFLAGS"

  cd "$ROOT"

  handle_executable "$build_dir/tools/autotools" "${tsk_executables[@]}"
  handle_executable "$build_dir/tools/fstools"   "${fs_executables[@]}"
  handle_executable "$build_dir/tools/imgtools"  "${img_executables[@]}"
}

hfuzz_compile() {
  export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions -std=c++17"
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  build_dir="build-hfuzz"
  rm -rf "$build_dir" && mkdir "$build_dir"

  cd "$build_dir"
  ../"$target"/configure --disable-shared --enable-static \
    CC="$CC" CXX="$CXX"

  make -j"$(nproc)" V=1 CC="$CC" CXX="$CXX"
  cd "$ROOT"

  copy_executable "$build_dir/tools/autotools" "${tsk_executables[@]}"
  copy_executable "$build_dir/tools/fstools"   "${fs_executables[@]}"
  copy_executable "$build_dir/tools/imgtools"  "${img_executables[@]}"
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

cd "$ROOT"
compile

