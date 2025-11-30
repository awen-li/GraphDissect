#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="jsoncpp"
executables=("jsontestrunner_exe" "jsoncpp_test")

Action="$1"

source ../__scripts__/base.sh

JSONCPP_REPO="https://github.com/open-source-parsers/jsoncpp.git"

initialize() {
    # Always use fresh latest code
    if [ -d "$target" ]; then
        rm -rf "$target"
    fi

    git clone --depth 1 "${JSONCPP_REPO}" "$target" || {
        echo "[jsoncpp] ERROR: git clone failed"
        exit 1
    }
}

wllvm_compile() {
    initialize

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

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DJSONCPP_WITH_TESTS=ON \
        -DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF \
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/build/bin" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build -j8

    cd "$ROOT"

    handle_executable "$target/build/bin" "${executables[@]}"
}

hfuzz_compile() {
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DJSONCPP_WITH_TESTS=ON \
        -DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF \
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/build/bin" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo

    cmake --build build -j8

    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
