#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="http-parser"
executables=("url_parser" "parsertrace")

Action="$1"

source ../__scripts__/base.sh

initialize() 
{
    if [ -d "$target" ]; then
       rm -rf "$target" 
    fi
    echo "[http-parser] cloning upstream repo..."
    git clone --depth 1 https://github.com/nodejs/http-parser.git "$target"
}

wllvm_compile() 
{
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

    cd "$target"
    make clean || true
    make -j8 CC="$CC" url_parser parsertrace
    cd "$ROOT"

    handle_executable "$target" "${executables[@]}"
}

hfuzz_compile() 
{
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export CFLAGS="$COMMON_FLAGS"
    export CXXFLAGS="$COMMON_FLAGS"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    cd "$target"
    make clean || true
    make -j8 CC="$CC" url_parser parsertrace
    cd "$ROOT"

    copy_executable "$target" "${executables[@]}"
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
