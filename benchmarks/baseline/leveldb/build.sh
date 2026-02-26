#!/usr/bin/env bash
set -euxo pipefail

export ROOT="$(pwd)"
export target="leveldb"

Action="${1:-}"
executables=("leveldbutil")

# load shared helpers (clean/show/compile/handle_executable/copy_executable ...)
source ../__scripts__/base.sh

function initialize ()
{
    if [ ! -d "$target" ]; then
        git clone https://github.com/google/leveldb.git "$target"
    fi
}

function wllvm_compile ()
{
    export CC=wllvm
    export CXX=wllvm++

    COMMON_FLAGS="-g -O2 -save-temps=obj \
        -fno-discard-value-names \
        -fno-inline-functions \
        -fno-inline-functions-called-once \
        -mllvm -inline-threshold=0 \
        -w"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"
    cd "$build_dir"

    cmake -G "Unix Makefiles" ../"$target" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_CXX_STANDARD=17 \
        -DLEVELDB_BUILD_TESTS=OFF \
        -DLEVELDB_BUILD_BENCHMARKS=OFF
    make -j"$(nproc)"
    cd ..

    handle_executable "$build_dir" "${executables[@]}"
}

function hfuzz_compile ()
{
    export CC=hfuzz-clang
    export CXX=hfuzz-clang++

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions -w"
    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="-std=c++17 $COMMON_FLAGS"

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"
    cd "$build_dir"

    cmake -G "Unix Makefiles" ../"$target" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_CXX_STANDARD=17 \
        -DLEVELDB_BUILD_TESTS=OFF \
        -DLEVELDB_BUILD_BENCHMARKS=OFF
    make -j"$(nproc)"
    cd ..

    copy_executable "$build_dir" "${executables[@]}"
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
initialize
compile
