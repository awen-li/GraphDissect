#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="file_src"
executables=("file")

Action="$1"

source ../__scripts__/base.sh

FILE_REPO="https://github.com/file/file.git"

initialize() 
{
    if [ ! -d "$target" ]; then
        echo "[file] cloning upstream repo..."
        git clone --depth 1 "$FILE_REPO" "$target" || {
            echo "[file] ERROR: git clone failed"
            exit 1
        }
    fi

    # "file" uses autotools; repo usually needs autoreconf
    cd "$target"
    if [ -x "./autogen.sh" ]; then
        ./autogen.sh
    elif [ ! -f "./configure" ]; then
        mkdir -p m4
        libtoolize -f -c || true
        export ACLOCAL_PATH="/usr/share/aclocal"
        autoreconf -vfi || {
            echo "[file] ERROR: autoreconf failed"
            exit 1
        }
    fi
    cd "$ROOT"

    export ac_cv_header_zstd_h=no
    export ac_cv_lib_zstd_ZSTD_createDCtx=no
    export ac_cv_lib_zstd_ZSTD_DCtx_reset=no
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
                  -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"

    cd "$target"
    ./configure \
        --disable-shared \
        --enable-static \
        --disable-dependency-tracking 
    make -j8
    cd "$ROOT"

    # binary is under src/
    handle_executable "$target/src" "${executables[@]}"
}

hfuzz_compile() 
{
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-g -O2 \
                  -fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    ./configure \
        --disable-shared \
        --enable-static \
        --disable-dependency-tracking
    make -j8
    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
