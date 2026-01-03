#!/usr/bin/env bash
set -euo pipefail

export ROOT="$(pwd)"
export target="snort3"
Action="${1:-}"

executables=("snort2lua")
executables1=("snort")

source ../__scripts__/base.sh

initialize() {
    export PATH=/usr/local/bin:$PATH

    if [ ! -d "$target" ]; then
        echo "[snort3] cloning upstream repo..."
        git clone --depth 1 --recursive https://github.com/snort3/snort3.git "$target"
    fi

    command -v cmake >/dev/null 2>&1 || { echo "[snort3] ERROR: cmake not found"; exit 1; }
}

wllvm_compile() {
    export CC='wllvm -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w'
    export CXX='wllvm++ -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w'

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir -p "$build_dir"

    ( cd "$build_dir" \
         && cmake "../$target" \
         -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF \
         -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
         -DCMAKE_PREFIX_PATH=/opt/daq \
         -DDAQ_INCLUDE_DIR=/opt/daq/include \
         -DDAQ_LIBRARIES=/opt/daq/lib/libdaq.a \
         && make -j4 \
    )

    handle_executable "$build_dir/tools/snort2lua" "${executables[@]}"
    handle_executable "$build_dir/src" "${executables1[@]}"
}

hfuzz_compile() {
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir -p "$build_dir"

    ( cd "$build_dir" \
         && cmake "../$target" \
         -DCMAKE_BUILD_TYPE=Release \
         -DBUILD_SHARED_LIBS=OFF \
         -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
         -DCMAKE_PREFIX_PATH=/opt/daq \
         -DDAQ_INCLUDE_DIR=/opt/daq/include \
         -DDAQ_LIBRARIES=/opt/daq/lib/libdaq.a \
         && make -j4 \
    ) 

    copy_executable "$build_dir/tools/snort2lua" "${executables[@]}"
}

# -------- actions --------
if [ "$Action" = "clean" ]; then
    exe="${2:-}"
    if [ -n "$exe" ]; then
        targets=("$exe")
    else
        targets=("${executables[@]}")
    fi
    clean "${targets[@]}"
    exit 0
fi

if [ "$Action" = "show" ]; then
    show_driver_info "${executables[@]}"
    exit 0
fi

cd "$ROOT"
compile

