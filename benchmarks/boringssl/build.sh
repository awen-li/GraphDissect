#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="boringssl"
executables=("bssl")

Action="$1"

source ../__scripts__/base.sh

BORINGSSL_REPO="https://boringssl.googlesource.com/boringssl"

initialize()
{
    if [ ! -d "$target" ]; then
        echo "[boringssl] cloning upstream repo..."
        git clone --depth 1 "$BORINGSSL_REPO" "$target" || {
            echo "[boringssl] ERROR: git clone failed"
            exit 1
        }
    fi
}

wllvm_compile()
{
    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"

    cd "$target"
    build=wllvm_build
    rm -rf $build
    mkdir -p $build

    cd $build
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF
    cmake --build . -j8 --target bssl
    cd "$ROOT"

    handle_executable "$target/$build" "${executables[@]}"
}

hfuzz_compile()
{
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-g -O2 \
                  -fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    build=hfuzz_build
    rm -rf $build
    mkdir -p $build

    cd $build
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF
    cmake --build . -j8 --target bssl
    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
