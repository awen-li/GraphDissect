#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="cpython3"

Action="$1"
# main binary we care about
executables=("python")

# load library
source ../__scripts__/base.sh

ensure_configure() {
    if [ ! -f "$target/configure" ]; then
        echo "[cpython3] ERROR: configure script missing in $target"
        exit 1
    fi
}

initialize() {
    if [ ! -d "$target" ]; then
        echo "[cpython3] cloning upstream repo..."
        git clone --depth 1 https://github.com/python/cpython.git "$target"
    fi

    ensure_configure
}

wllvm_compile() {
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 -save-temps=obj \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0 \
                  -w"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"

    build_dir="build-wllvm"
    if [ ! -d "$build_dir" ]; then
        mkdir "$build_dir"
    fi

    cd "$build_dir"
    ../$target/configure
    make -j8
    cd "$ROOT"

    handle_executable "$build_dir" "${executables[@]}"
}

hfuzz_compile() {
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    build_dir="build-hfuzz"
    if [ ! -d "$build_dir" ]; then
        mkdir "$build_dir"
    fi

    cd "$build_dir"
    ../$target/configure
    make -j8
    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    exe="$2"
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
