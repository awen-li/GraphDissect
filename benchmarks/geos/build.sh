#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="geos"
executables=("geosop")

Action="$1"

source ../__scripts__/base.sh

initialize() 
{
    if [ ! -d "$target" ]; then
        echo "[geos] cloning upstream repo..."
        git clone --depth 1 https://git.osgeo.org/gitea/geos/geos.git "$target" || {
            echo "[geos] ERROR: git clone failed"
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
    cmake -S . -B $build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF

    cmake --build $build -j8
    cd "$ROOT"

    handle_executable "$target/$build/bin" "${executables[@]}"
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

    cd "$target"
    build=hfuzz_build
    rm -rf $build
    cmake -S . -B $build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF

    cmake --build $build -j8
    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
