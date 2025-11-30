#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="hdf5"
executables=("h5dump" "h5ls" "h5diff" "h5stat" "h5repack")

Action="$1"

source ../__scripts__/base.sh

HDF5_REPO="https://github.com/HDFGroup/hdf5.git"

initialize() {
    if [  -d "$target" ]; then
        return
    fi

    echo "[hdf5] cloning upstream repo..."
    git clone --depth 1 "${HDF5_REPO}" "$target" || {
        echo "[hdf5] ERROR: git clone failed"
        exit 1
    }
}

wllvm_compile() {
    initialize

    export LLVM_COMPILER=clang
    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_C_FLAGS="-g -O2 \
                    -fno-discard-value-names \
                    -fno-inline-functions \
                    -fno-inline-functions-called-once \
                    -mllvm -inline-threshold=0"

    COMMON_CXX_FLAGS="${COMMON_C_FLAGS} -std=gnu++17"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_CXX_FLAGS}"

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DHDF5_BUILD_TOOLS=ON \
        -DHDF5_BUILD_EXAMPLES=OFF \
        -DHDF5_BUILD_TESTING=OFF \
        -DHDF5_BUILD_HL_LIB=ON \
        -DBUILD_SHARED_LIBS=OFF \
        -DBUILD_STATIC_LIBS=ON \
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/build/bin"

    cmake --build build -j8

    cd "$ROOT"

    handle_executable "$target/build/bin" "${executables[@]}"
}

hfuzz_compile() {
    initialize

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_C_FLAGS="-g -O2 \
                    -fsanitize-coverage=trace-pc-guard \
                    -finstrument-functions"

    COMMON_CXX_FLAGS="${COMMON_C_FLAGS} -std=gnu++17"

    export CFLAGS="${COMMON_C_FLAGS}"
    export CXXFLAGS="${COMMON_CXX_FLAGS}"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"

    rm -rf build
    cmake -S . -B build \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DCMAKE_BUILD_TYPE=RelWithDebInfo \
        -DHDF5_BUILD_TOOLS=ON \
        -DHDF5_BUILD_EXAMPLES=OFF \
        -DHDF5_BUILD_TESTING=OFF \
        -DHDF5_BUILD_HL_LIB=ON \
        -DBUILD_SHARED_LIBS=OFF \
        -DBUILD_STATIC_LIBS=ON \
        -DCMAKE_RUNTIME_OUTPUT_DIRECTORY="${PWD}/build/bin"

    cmake --build build -j8

    cd "$ROOT"
}

if [ "${Action}" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
