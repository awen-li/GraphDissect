#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="curl"

Action="$1"
executables=("curl")

# load library
source ../__scripts__/base.sh


ensure_configure() {
    # Generate ./configure from configure.ac using autoreconf
    if [ ! -f "$target/configure" ]; then
        echo "[curl] configure not found, running autoreconf -fi..."
        (
            cd "$target"
            autoreconf -fi
        )
    fi
    if [ ! -f "$target/configure" ]; then
        echo "[curl] ERROR: configure script still missing in $target"
        exit 1
    fi
}


initialize() {
    if [ ! -d "$target" ]; then
        echo "[curl] cloning upstream repo..."
        git clone --depth 1 https://github.com/curl/curl.git "$target"
    fi

    ensure_configure
}

wllvm_compile() {

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

    build_dir="build-wllvm"
    if [ ! -d "$build_dir" ]; then
        mkdir "$build_dir"
    fi

    cd "$build_dir"
    ../$target/configure --enable-shared=no --without-ssl --without-libpsl
    make -j8
    cd "$ROOT"

    handle_executable "$build_dir/src" "${executables[@]}"
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
    ../$target/configure --enable-shared=no --without-ssl --without-libpsl
    make -j8
    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
