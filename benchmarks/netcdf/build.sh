#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="netcdf_source"

executables=("ncdump" "nccopy")
executables_ncgen=("ncgen")

Action="$1"

source ../__scripts__/base.sh

initialize() {
    if [ ! -d "$target" ]; then
        echo "[netcdf] cloning upstream repo..."
        git clone --depth 1 https://github.com/Unidata/netcdf-c "$target"
    fi
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

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    cmake ../"$target" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_CXX_FLAGS="$CXXFLAGS" \
        -DBUILD_SHARED_LIBS=OFF \
        -DENABLE_TESTS=OFF \
        -DENABLE_EXAMPLES=OFF \
        -DENABLE_DAP=OFF \
        -DENABLE_HDF5=OFF \
        -DENABLE_NETCDF_4=OFF
    make -j"$(nproc)"
    cd "$ROOT"

    handle_executable "$build_dir/ncdump" "${executables[@]}"

    executables=("${executables_ncgen[@]}")
    handle_executable "$build_dir/ncgen"  "${executables[@]}"
}

hfuzz_compile() {
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"
    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    cmake ../"$target" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$COMMON_FLAGS" \
        -DCMAKE_CXX_FLAGS="$COMMON_FLAGS" \
        -DBUILD_SHARED_LIBS=OFF \
        -DENABLE_TESTS=OFF \
        -DENABLE_EXAMPLES=OFF \
        -DENABLE_DAP=OFF \
        -DENABLE_HDF5=OFF \
        -DENABLE_NETCDF_4=OFF
    make -j"$(nproc)"
    cd "$ROOT"

    copy_executable "$build_dir/ncdump" "${executables[@]}"

    executables=("${executables_ncgen[@]}")
    copy_executable "$build_dir/ncgen"  "${executables[@]}"
}

if [ "$Action" == "clean" ]; then
    exe="$2"
    if [ -n "$exe" ]; then
        targets=("$exe")
    else
        targets=("${executables[@]}")
    fi

    clean "${targets[@]}"
    clean "${executables_ncgen[@]}"
    exit 0
fi

if [ "$Action" == "show" ]; then
    show_driver_info "${executables[@]}"
    show_driver_info "${executables_ncgen[@]}"
    exit 0
fi

cd "$ROOT"
compile
