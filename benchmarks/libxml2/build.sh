#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libxml2"

Action="$1"
executables=("xmllint")

# load library
source ../__scripts__/base.sh

ensure_configure() {
    # Generate ./configure if we cloned from git and only have autogen.sh
    if [ ! -f "$target/configure" ] && [ -x "$target/autogen.sh" ]; then
        echo "[libxml2] configure not found, running autogen.sh..."
        ( cd "$target" && NOCONFIGURE=1 ./autogen.sh )
    fi
    if [ ! -f "$target/configure" ]; then
        echo "[libxml2] ERROR: configure script still missing in $target"
        exit 1
    fi
}

initialize() {
    export PKG_CONFIG_PATH="/root/anaconda3/lib/pkgconfig:${PKG_CONFIG_PATH:-}"

    if [ ! -d "$target" ]; then
        echo "[libxml2] cloning upstream repo..."
        git clone --depth 1 https://gitlab.gnome.org/GNOME/libxml2.git "$target"
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

    ensure_configure

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    ../$target/configure --enable-shared=no
    make -j4
    cd "$ROOT"
}

hfuzz_compile() {
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    ensure_configure

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    ../$target/configure --enable-shared=no
    make -j4
    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
