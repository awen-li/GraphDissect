#!/usr/bin/env bash
set -euxo pipefail

export ROOT="$(pwd)"
export target="liboqs-src"

# Representative liboqs examples (executables)
executables=("dump_alg_info" "example_sig" "kat_kem")

Action="${1:-}"

source ../__scripts__/base.sh

LIBOQS_REPO_URL="https://github.com/open-quantum-safe/liboqs.git"
initialize()
{
    if [ ! -d "$target" ]; then
        git clone --depth 1 $LIBOQS_REPO_URL $target
    fi

    rm -rf ${ROOT}/build-wllvm ${ROOT}/build-hfuzz
}

wllvm_compile()
{
    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -mllvm -inline-threshold=0 \
                  -fno-PIE"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LDFLAGS="-no-pie"

    build=build-wllvm
    cmake -S "${ROOT}/${target}" -B "${ROOT}/$build" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_C_COMPILER="${CC}" \
        -DCMAKE_C_FLAGS="${CFLAGS}" \
        -DCMAKE_EXE_LINKER_FLAGS="${LDFLAGS}" \
        -DOQS_BUILD_ONLY_LIB=OFF \
        -DOQS_BUILD_SHARED_LIBS=OFF \
        -DOQS_BUILD_EXAMPLES=ON \
        -DOQS_BUILD_TESTS=OFF
    cmake --build "${ROOT}/$build" -j8

    handle_executable "${ROOT}/$build/tests" "${executables[@]}"
}

hfuzz_compile()
{
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-g -O2 \
                  -fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions \
                  -fno-PIE"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LDFLAGS="-no-pie"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cmake -S "${ROOT}/${target}" -B "${ROOT}/build-hfuzz" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DCMAKE_C_COMPILER="${CC}" \
        -DCMAKE_C_FLAGS="${CFLAGS}" \
        -DCMAKE_EXE_LINKER_FLAGS="${LDFLAGS}" \
        -DOQS_BUILD_ONLY_LIB=OFF \
        -DOQS_BUILD_SHARED_LIBS=OFF \
        -DOQS_BUILD_EXAMPLES=ON \
        -DOQS_BUILD_TESTS=OFF
    cmake --build "${ROOT}/build-hfuzz" -j8
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
