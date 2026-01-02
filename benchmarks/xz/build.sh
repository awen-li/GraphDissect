#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="xz_source"

executables=("xz")

Action="$1"

source ../__scripts__/base.sh

ensure_configure() 
{
    # xz uses autotools. In git checkouts, configure may need autoreconf.
    if [ ! -f "$target/configure" ]; then
        echo "[xz] configure script missing; running autogen..."
        (cd "$target" && ./autogen.sh) || true
        (cd "$target" && autoreconf -fi) || true
    fi
    if [ ! -f "$target/configure" ]; then
        echo "[xz] ERROR: configure script missing in $target"
        exit 1
    fi
}

initialize() 
{
    if [-d "$target" ]; then
        rm -rf "$target"        
    fi
    git clone --depth 1 https://github.com/tukaani-project/xz.git "$target"
    ensure_configure
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
    ./configure --disable-doc --disable-shared --disable-nls CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" 
    make -j"$(nproc)"
    cd "$ROOT"

    handle_executable "$target/src/xz" $executables
}

hfuzz_compile() 
{
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    ./configure --disable-doc --disable-shared --disable-nls
    make -j"$(nproc)"
    cd "$ROOT"

    handle_executable "$target/src/xz" $executables
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
