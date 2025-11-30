#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="rocksdb"
executables=("db_bench")

Action="$1"

source ../__scripts__/base.sh

ROCKSDB_REPO="https://github.com/facebook/rocksdb.git"

initialize() {
    # Always use latest code from repo
    if [ -d "$target" ]; then
        rm -rf "$target"
    fi

    echo "[rocksdb] cloning upstream repo..."
    git clone --depth 1 "${ROCKSDB_REPO}" "$target" || {
        echo "[rocksdb] ERROR: git clone failed"
        exit 1
    }
}

wllvm_compile() {
    initialize

    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_C_FLAGS="-g -O2 \
                    -fno-discard-value-names \
                    -fno-inline-functions"

    COMMON_CXX_FLAGS="${COMMON_C_FLAGS} -std=gnu++17"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_CXX_FLAGS}"

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DROCKSDB_BUILD_SHARED=OFF \
        -DWITH_TESTS=ON \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    # Correct build syntax: specify target via --target
    cmake --build build --target db_bench -j8

    cd "$ROOT"

    handle_executable "$target/build" "${executables[@]}"
}

hfuzz_compile() {
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_C_FLAGS="-g -O2 \
                    -fsanitize-coverage=trace-pc-guard \
                    -finstrument-functions"

    COMMON_CXX_FLAGS="${COMMON_C_FLAGS} -std=gnu++17"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_CXX_FLAGS}"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DROCKSDB_BUILD_SHARED=OFF \
        -DWITH_TESTS=ON \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build --target db_bench -j8

    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
