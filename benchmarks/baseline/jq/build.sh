#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="jq_source"

executables=("jq")

Action="$1"

source ../__scripts__/base.sh

ensure_configure() 
{
    cd "$target"
    libtoolize --force --copy
    autoreconf -fvi
    cd "$ROOT"
}

initialize() 
{
    if [ -d "$target" ]; then
        rm -rf "$target"
    fi
    git clone --depth 1 https://github.com/jqlang/jq.git "$target"
    ensure_configure
    apt-get install -y libonig-dev
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

    cd $target
    ./configure CC="$CC" CXX="$CXX" CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" --disable-maintainer-mode --disable-shared
    make -j"$(nproc)"
    cd "$ROOT"

    handle_executable "$target" "${executables[@]}"
}

hfuzz_compile() 
{
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd $target
    ./configure CC="$CC" CXX="$CXX" --disable-maintainer-mode --disable-shared
    make -j"$(nproc)"
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
