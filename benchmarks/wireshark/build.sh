#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="wireshark"

Action="$1"
# Treat all core CLIs as executables for GraphDissect
executables=("tshark" "editcap" "capinfos")

# load library helpers (compile, clean, handle_executable, etc.)
source ../__scripts__/base.sh

initialize() {
    if [ ! -d "$target" ]; then
        echo "[wireshark] cloning upstream repo..."
        git clone --depth 1 https://gitlab.com/wireshark/wireshark.git "$target"
    fi

    #apt-get update && apt-get install -y libglib2.0-dev libpcap-dev zlib1g-dev libgcrypt20-dev \
    #         liblz4-dev libzstd-dev libnghttp2-dev flex bison
    #apt-get install -y libc-ares-dev libxml2-dev libspeexdsp-dev libpcre2-dev
}


wllvm_compile() {

    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-pg -g -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -w"

    # Tell the linker where to find libstdc++
    STDCPP_DIR="/usr/lib/gcc/x86_64-linux-gnu/11"
    ALT_LIBDIR="/usr/lib/x86_64-linux-gnu"
    LINK_FLAGS="-L${STDCPP_DIR} -L${ALT_LIBDIR}"

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"
    cd "$build_dir"

    cmake ../"$target" \
        -DBUILD_wireshark=OFF \
        -DBUILD_qt_ui=OFF \
        -DENABLE_APPLICATION_BUNDLE=OFF \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$COMMON_FLAGS" \
        -DCMAKE_CXX_FLAGS="$COMMON_FLAGS" \
        -DCMAKE_EXE_LINKER_FLAGS="$LINK_FLAGS" \
        -DCMAKE_SHARED_LINKER_FLAGS="$LINK_FLAGS"

    make -j8 "${executables[@]}"

    cd "$ROOT"
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ROOT/build-wllvm/run
    handle_executable "$build_dir/run" "${executables[@]}"
}



hfuzz_compile() {

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    # Same libstdc++ dirs for clang/hfuzz-clang
    STDCPP_DIR="/usr/lib/gcc/x86_64-linux-gnu/11"
    ALT_LIBDIR="/usr/lib/x86_64-linux-gnu"
    LINK_FLAGS="-L${STDCPP_DIR} -L${ALT_LIBDIR}"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"
    cd "$build_dir"
    
    cmake ../"$target" \
        -DBUILD_wireshark=OFF \
        -DBUILD_qt_ui=OFF \
        -DENABLE_APPLICATION_BUNDLE=OFF \
        -DCMAKE_C_COMPILER="$CC" \
        -DCMAKE_CXX_COMPILER="$CXX" \
        -DCMAKE_C_FLAGS="$COMMON_FLAGS" \
        -DCMAKE_CXX_FLAGS="$COMMON_FLAGS" \
        -DCMAKE_EXE_LINKER_FLAGS="$LINK_FLAGS" \
        -DCMAKE_SHARED_LINKER_FLAGS="$LINK_FLAGS"

    make -j8 "${executables[@]}"

    cd "$ROOT"
}



if [ "$Action" == "clean" ]; then
    clean
    exit 0
fi

cd "$ROOT"
compile
