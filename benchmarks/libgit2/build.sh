#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libgit2"

# Main driver binary: libgit2 example CLI
#commit_graph_fuzzer  config_file_fuzzer  download_refs_fuzzer  lg2  
#midx_fuzzer  objects_fuzzer  packfile_fuzzer  patch_parse_fuzzer  revparse_fuzzer
executables=("commit_graph_fuzzer" "objects_fuzzer" "packfile_fuzzer")


Action="$1"

source ../__scripts__/base.sh

LIBGIT2_REPO="https://github.com/libgit2/libgit2.git"

initialize() {
  if [ -d "$target" ]; then
    return
  fi

  echo "[libgit2] cloning upstream repo..."
  git clone --depth 1 "${LIBGIT2_REPO}" "$target" || {
    echo "[libgit2] ERROR: git clone failed"
    exit 1
  }
}

wllvm_compile() {

  export LLVM_COMPILER=clang
  export CC="wllvm"
  export CXX="wllvm++"

  COMMON_C_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0"

  export CFLAGS="${COMMON_C_FLAGS}"
  export CXXFLAGS="${COMMON_C_FLAGS}"

  cd "$target"

  build=wllmv_build
  rm -rf $build
  cmake -S . -B $build \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_C_FLAGS="$CFLAGS" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBUILD_SHARED_LIBS=OFF \
    -DBUILD_TESTS=OFF \
    -DBUILD_CLI=OFF \
    -DBUILD_EXAMPLES=ON \
    -DUSE_SSH=OFF \
    -DUSE_HTTPS=OFF \
    -DUSE_BUNDLED_ZLIB=ON \
    -DUSE_NTLMCLIENT=OFF \
    -DBUILD_FUZZERS=ON \
    -DUSE_STANDALONE_FUZZERS=ON \
    -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/$build/bin"

  # build the example CLI driver
  cmake --build $build -j8

  cd "$ROOT"

  handle_executable "$target/$build/bin" "${executables[@]}"
}

hfuzz_compile() {

  export CC="hfuzz-clang"
  export CXX="hfuzz-clang++"

  COMMON_C_FLAGS="-g -O2 \
                  -fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

  export CFLAGS="${COMMON_C_FLAGS}"
  export CXXFLAGS="${COMMON_C_FLAGS}"
  export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

  cd "$target"

  build=hfuzz_build
  rm -rf $build
  cmake -S . -B $build \
    -DCMAKE_C_COMPILER="$CC" \
    -DCMAKE_C_FLAGS="$CFLAGS" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBUILD_SHARED_LIBS=OFF \
    -DBUILD_TESTS=OFF \
    -DBUILD_CLI=OFF \
    -DBUILD_EXAMPLES=ON \
    -DUSE_SSH=OFF \
    -DUSE_HTTPS=OFF \
    -DUSE_BUNDLED_ZLIB=ON \
    -DUSE_NTLMCLIENT=OFF \
    -DBUILD_FUZZERS=ON \
    -DUSE_STANDALONE_FUZZERS=ON \
    -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/$build/bin"

  cmake --build $build -j8

  cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
  clean
  exit 0
fi

cd "$ROOT"
compile
