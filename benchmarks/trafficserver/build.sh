#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="trafficserver"
executables=("traffic_server")

Action="$1"

source ../__scripts__/base.sh

ATS_REPO="https://github.com/apache/trafficserver.git"

initialize() {
    if [ ! -d "$target" ]; then
        echo "[trafficserver] cloning upstream repo..."
        git clone --depth 1 "${ATS_REPO}" "${target}" || {
            echo "[trafficserver] ERROR: git clone failed"
            exit 1
        }
    fi
}

wllvm_compile() {
    initialize

    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-pg -g -O2 -save-temps=obj \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0 \
                  -w"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"

    cd "$target"

    # Fresh CMake build directory
    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build -j8

    cd "$ROOT"

    # Register the main binary (for wllvm bitcode extraction, etc.)
    handle_executable "$target/build/src/" "${executables[@]}"
}

hfuzz_compile() {
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build -j8

    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
