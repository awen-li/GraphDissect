#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="xpdf-4.05"

Action="$1"
executables=("pdfdetach" "pdfimages" "pdftohtml" "pdftoppm" "pdftotext" "pdffonts" "pdfinfo" "pdftopng" "pdftops")

# load library
source ../__scripts__/base.sh

initialize() {
    export PKG_CONFIG_PATH=/root/anaconda3/lib/pkgconfig:$PKG_CONFIG_PATH

    if [ ! -d "$target" ]; then
        tar -xvf xpdf-4.05.tar.gz
    fi
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

    if [ -d "build" ]; then rm -rf build; fi
    mkdir build && cd build
    cmake "../$target"
    make -j4
    cd "$ROOT"

    handle_executable "build/xpdf" "${executables[@]}"
}

hfuzz_compile() {
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    if [ -d "build" ]; then rm -rf build; fi
    mkdir build && cd build

    cmake "../$target"
    make -j4

    cd "$ROOT"
}

if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
