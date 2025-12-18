#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libecc"
executables=("ec_utils")

Action="$1"

source ../__scripts__/base.sh

LIBECC_REPO="https://github.com/ANSSI-FR/libecc.git"

initialize() 
{
    if [ -d "$target" ]; then
        rm -rf $target
    fi
    echo "[libecc] cloning upstream repo..."
    git clone --depth 1 "$LIBECC_REPO" "$target"
}

wllvm_compile() 
{
    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -fno-PIE -no-pie"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LDFLAGS="-no-pie"

    cd "$target"
    make -j8
    cd "$ROOT"

    handle_executable "$target/build" "${executables[@]}"
}

hfuzz_compile()
{
    echo "[libecc] hfuzz_compile"
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-g -O2 \
                  -fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions \
                  -fno-PIE -no-pie"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LDFLAGS="-no-pie"

    cd "$target"
    make -j8
    cd "$ROOT"

}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
