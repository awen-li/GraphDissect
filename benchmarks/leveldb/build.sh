#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="leveldb"
executables=("db_bench" "leveldbutil")

Action="$1"

source ../__scripts__/base.sh

LEVELDB_REPO="https://github.com/google/leveldb.git"

initialize() 
{
    if [ ! -d "$target" ]; then
        echo "[leveldb] cloning upstream repo..."
        git clone --depth 1 --recurse-submodules "$LEVELDB_REPO" "$target" || {
            echo "[leveldb] ERROR: git clone failed"
            exit 1
        }
    else
        # in case it was cloned without submodules before
        ( cd "$target" && git submodule update --init --recursive ) || true
    fi
}


wllvm_compile() 
{
    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"

    cd "$target"

    build=wllvm_build
    rm -rf $build
    mkdir -p $build

    cd $build
    cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CXX_STANDARD=17 \
        -DCMAKE_CXX_STANDARD_REQUIRED=ON \
        -DBUILD_SHARED_LIBS=OFF
    cmake --build . -j8
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
        -DCMAKE_CXX_STANDARD=17 \
        -DCMAKE_CXX_STANDARD_REQUIRED=ON \
        -DBUILD_SHARED_LIBS=OFF

    cmake --build . -j8
    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
