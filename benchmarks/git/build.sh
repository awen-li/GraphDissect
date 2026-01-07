#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="git_source"


executables=("git")

Action="${1:-}"

source ../__scripts__/base.sh

ensure_configure() {
    if [ ! -f "$target/configure" ]; then
        echo "[git] configure script missing; generating with 'make configure'..."
        (cd "$target" && make configure)
    fi

    if [ ! -f "$target/configure" ]; then
        echo "[git] ERROR: configure script still missing in $target"
        exit 1
    fi
}

initialize() {
    if [ ! -d "$target" ]; then
        echo "[git] cloning upstream repo..."
        git clone --depth 1 https://github.com/git/git "$target"
    fi
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
    export LDFLAGS="-pg"

    cd "$target"

    # Clean previous config/build (Git does not support your FFmpeg-style out-of-tree reliably)
    make distclean >/dev/null 2>&1 || true

    ./configure CC="$CC" HOSTCC=clang CFLAGS="$CFLAGS" LDFLAGS="$LDFLAGS"

    make CC="$CC" CFLAGS="$COMMON_FLAGS" -j"$(nproc)"

    cd "$ROOT"

    # Copy from source dir (where binaries are produced)
    handle_executable "$target" "${executables[@]}"
}


hfuzz_compile() 
{
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"

    make distclean >/dev/null 2>&1 || true
    ./configure CC="$CC"

    make -j"$(nproc)"

    cd "$ROOT"

    copy_executable "$target" "${executables[@]}"
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
compile

