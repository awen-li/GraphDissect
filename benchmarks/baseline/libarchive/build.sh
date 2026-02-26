#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libarchive"

# CLI tools as drivers (paths relative to $target)
executables=(
    "bsdtar"
    "bsdunzip"
)

Action="$1"

source ../__scripts__/base.sh

LIBARCHIVE_VERSION="3.8.3"
LIBARCHIVE_TARBALL="libarchive-${LIBARCHIVE_VERSION}.tar.xz"
LIBARCHIVE_URL="https://www.libarchive.org/downloads/${LIBARCHIVE_TARBALL}"

initialize() 
{
    # Always start from a clean source tree
    if [ -d "$target" ]; then
        rm -rf "$target"
    fi

    if [ ! -f "$LIBARCHIVE_TARBALL" ]; then
        echo "[libarchive] downloading ${LIBARCHIVE_TARBALL}..."
        wget -q "${LIBARCHIVE_URL}" -O "${LIBARCHIVE_TARBALL}" || {
            echo "[libarchive] ERROR: failed to download ${LIBARCHIVE_TARBALL}"
            exit 1
        }
    fi

    echo "[libarchive] extracting ${LIBARCHIVE_TARBALL}..."
    tar xf "${LIBARCHIVE_TARBALL}"
    mv "libarchive-${LIBARCHIVE_VERSION}" "${target}"
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

    # Using the pre-generated configure from the tarball:
    make distclean >/dev/null 2>&1 || true

    ./configure \
        --enable-static \
        --disable-shared

    make -j8

    cd "$ROOT"

    handle_executable "$target" "${executables[@]}"
}

hfuzz_compile() 
{
    export CC="hfuzz-clang -g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    make distclean >/dev/null 2>&1 || true
    ./configure \
        --enable-static \
        --disable-shared
    make -j8
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
