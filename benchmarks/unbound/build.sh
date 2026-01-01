#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="unbound_src"
executables=("unbound-checkconf")

Action="${1:-}"

source ../__scripts__/base.sh

UNBOUND_REPO="https://github.com/NLnetLabs/unbound.git"

initialize() 
{
    if [ -d "$target" ]; then
        return
    fi

    echo "[unbound] cloning upstream repo..."
    git clone --depth 1 "${UNBOUND_REPO}" "$target" || {
        echo "[unbound] ERROR: git clone failed"
        exit 1
    }
}

# Unbound uses autotools.
# We build static-ish (no shared) to make instrumentation simpler.
wllvm_compile() 
{

    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"  # mostly unused, but keep consistent

    COMMON_C_FLAGS="-g -O2\
                    -fno-discard-value-names \
                    -fno-inline-functions \
                    -fno-inline-functions-called-once \
                    -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_C_FLAGS}"

    cd "$target"

    # Autotools bootstrap if needed
    if [ ! -x "./configure" ]; then
        echo "[unbound] configure not found, running autogen.sh..."
        if [ -x "./autogen.sh" ]; then
            ./autogen.sh
        else
            autoreconf -fi
        fi
    fi

    rm -rf build-wllvm
    mkdir -p build-wllvm
    cd build-wllvm

    # Minimal features; avoid python/swig etc.
    # Note: --disable-shared gives static libunbound where possible.
    ../configure \
        CC="$CC" \
        CFLAGS="$CFLAGS" \
        --disable-shared \
        --enable-static \
        --disable-flto \
        --without-pythonmodule \
        --without-pyunbound \
        --without-libevent || {
            echo "[unbound] ERROR: configure failed"
            exit 1
        }

    make -j"$(nproc)"

    cd "$ROOT"

    # unbound binaries are in build dir; list the expected ones
    handle_executable "$target/build-wllvm" "${executables[@]}" 
}

hfuzz_compile() 
{

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"  # mostly unused
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    COMMON_C_FLAGS="-g -O2 \
                    -fsanitize-coverage=trace-pc-guard \
                    -finstrument-functions"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_C_FLAGS}"

    cd "$target"

    if [ ! -x "./configure" ]; then
        echo "[unbound] configure not found, running autogen.sh..."
        if [ -x "./autogen.sh" ]; then
            ./autogen.sh
        else
            autoreconf -fi
        fi
    fi

    rm -rf build-hfuzz
    mkdir -p build-hfuzz
    cd build-hfuzz

    ../configure \
        CC="$CC" \
        CFLAGS="$CFLAGS" \
        --disable-shared \
        --enable-static \
        --disable-flto \
        --without-pythonmodule \
        --without-pyunbound \
        --without-libevent || {
            echo "[unbound] ERROR: configure failed"
            exit 1
        }

    make -j"$(nproc)"

    cd "$ROOT"

    # For hfuzz runs we typically just copy the instrumented binaries out
    copy_executable "$target/build-hfuzz" "${executables[@]}"
}

# Standard control flow used in your other benchmarks
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

