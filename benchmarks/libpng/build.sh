#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libpng"
# CMake puts the tools in the build/ dir
executables=("pngfix" "pngimage" "pngtest" "pngunknown" "pngvalid")

Action="$1"

source ../__scripts__/base.sh

LIBPNG_REPO="https://github.com/pnggroup/libpng.git"

initialize() {
    # Always pull the latest code from the repository
    if [ -d "$target" ]; then
        rm -rf "$target"
    fi
    git clone --depth 1 "${LIBPNG_REPO}" "$target" || {
        echo "[libpng] ERROR: git clone failed"
        exit 1
    }

    apt-get install -y gawk
}

wllvm_compile() 
{
    initialize

    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"

    cd "$target"
    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DPNG_TESTS=ON \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo
    cmake --build build -j8
    cd "$ROOT"

    handle_executable "$target/build" "${executables[@]}"
}

hfuzz_compile() {
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DPNG_TESTS=ON \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build -j8

    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
