#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="sqlite3-src"

Action="${1:-compile}"
executables=("sqlite3")

# load library
source ../__scripts__/base.sh

initialize() {
  if [[ ! -d "$target" ]]; then
    echo "[sqlite3] cloning upstream repo..."
    git clone --depth 1 https://github.com/sqlite/sqlite.git "$target"
  fi

  # Many sqlite git checkouts do NOT ship ./configure.
  # If configure is missing, fail fast with a clear hint.
  if [[ ! -f "$target/configure" ]]; then
    echo "[sqlite3] ERROR: ./configure not found in git checkout." >&2
    echo "[sqlite3] Use the release tarball (sqlite-autoconf-*.tar.gz) OR provide configure/autogen." >&2
    exit 1
  fi
}

set_sqlite_feature_flags() {
  # Increase code surface in the CLI / parser / engine
  export CFLAGS="${CFLAGS:-} -O2 -g \
    -DSQLITE_ENABLE_FTS5 \
    -DSQLITE_ENABLE_JSON1 \
    -DSQLITE_ENABLE_RTREE \
    -DSQLITE_ENABLE_UPDATE_DELETE_LIMIT"
  export CXXFLAGS="${CXXFLAGS:-} -O2 -g"
}

wllvm_compile() {
  initialize
  set_sqlite_feature_flags

  # CC/CXX should be just the compiler wrapper; put flags in CFLAGS/CXXFLAGS
  export CC="wllvm"
  export CXX="wllvm++"

  build_dir="build-wllvm"
  rm -rf "$build_dir"
  mkdir "$build_dir"
  cd "$build_dir"

  "../$target/configure" --disable-shared
  make -j4 sqlite3
  cd - >/dev/null

  handle_executable "$build_dir" "${executables[@]}"
}

hfuzz_compile() {
  initialize
  set_sqlite_feature_flags

  export CC="hfuzz-clang"
  export CXX="hfuzz-clang++"

  # Your honggfuzz coverage knobs (if you want them globally)
  export CFLAGS="${CFLAGS} -fsanitize-coverage=trace-pc-guard -finstrument-functions"
  export CXXFLAGS="${CXXFLAGS} -fsanitize-coverage=trace-pc-guard -finstrument-functions"

  build_dir="build-hfuzz"
  rm -rf "$build_dir"
  mkdir "$build_dir"
  cd "$build_dir"

  "../$target/configure" --disable-shared
  make -j4 sqlite3
  cd - >/dev/null

  copy_executable "$build_dir" "${executables[@]}"
}

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
