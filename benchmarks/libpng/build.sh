#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libpng"
executables=("pngfix" "pngimage" "pngtest" "pngunknown" "pngvalid")

Action="$1"

source ../__scripts__/base.sh

ensure_configure() {
    if [ ! -f "$target/configure" ]; then
        echo "[libpng] 'configure' missing in $target, trying autoreconf/autogen..."
        if [ -x "$target/autogen.sh" ]; then
            ( cd "$target" && ./autogen.sh )
        else
            ( cd "$target" && autoreconf -fi || true )
        fi
        if [ ! -f "$target/configure" ]; then
            echo "[libpng] ERROR: configure script still missing in $target"
            exit 1
        fi
    fi
}

initialize() {

    if [ -d "$target" ]; then
        rm -rf "$target"
    fi
    git clone --depth 1 https://github.com/pnggroup/libpng.git "$target"

    ensure_configure()
    {
        if [ ! -f "$target/configure" ]; then
            echo "[libpng] 'configure' missing in $target, trying autoreconf/autogen..."
            if [ -x "$target/autogen.sh" ]; then
                ( cd "$target" && ./autogen.sh )
            else
                ( cd "$target" && autoreconf -fi || true )
            fi
            if [ ! -f "$target/configure" ]; then
                echo "[libpng] ERROR: configure script still missing in $target"
                exit 1
            fi
        fi
    }
    ensure_configure
}


wllvm_compile() {

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

    cd $target
    make distclean >/dev/null 2>&1 || true
    ./configure \
        --enable-static \
        --disable-shared
    make -j8
    cd $ROOT

    handle_executable "$target" "${executables[@]}"
}


hfuzz_compile() {

    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    make distclean >/dev/null 2>&1 || true
    ./configure \
        --enable-static \
        --disable-shared
    make -j8
    cd "$ROOT"
}


if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
