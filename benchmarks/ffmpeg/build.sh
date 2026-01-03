#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="ffmpeg_source"

executables=("ffmpeg" "ffprobe")

Action="$1"


source ../__scripts__/base.sh

ensure_configure() 
{
    if [ ! -f "$target/configure" ]; then
        echo "[ffmpeg] ERROR: configure script missing in $target"
        exit 1
    fi
}

initialize() 
{
    if [ ! -d "$target" ]; then
        echo "[ffmpeg] cloning upstream repo..."
        git clone --depth 1 https://github.com/FFmpeg/FFmpeg.git "$target"
    fi
    ensure_configure
}


wllvm_compile() 
{
    export LLVM_COMPILER=clang

    export CC="wllvm"
    export CXX="wllvm++"
    export AR="llvm-ar"
    export RANLIB="llvm-ranlib"
    export NM="llvm-nm"

    COMMON_FLAGS="-g -pg -O2 \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"
    export LDFLAGS="-pg"

    build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    ../"$target"/configure \
        --cc="$CC" \
        --cxx="$CXX" \
        --ar="$AR" \
        --ranlib="$RANLIB" \
        --nm="$NM" \
        --disable-debug \
        --disable-doc \
        --disable-ffplay \
        --disable-network \
        --disable-autodetect \
        --disable-stripping \
        --enable-static \
        --disable-shared \
        --disable-x86asm \
        --extra-cflags="$COMMON_FLAGS" \
        --extra-ldflags="-pg"
    make -j8
    cd "$ROOT"

    handle_executable "$build_dir" "${executables[@]}"
}


hfuzz_compile() 
{
    export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd "$build_dir"
    ../"$target"/configure \
        --cc="$CC" \
        --cxx="$CXX" \
        --disable-debug \
        --disable-doc \
        --disable-ffplay \
        --disable-network \
        --disable-autodetect \
        --disable-stripping \
        --enable-static \
        --disable-shared \
        --disable-x86asm
    make -j"$(nproc)"
    cd "$ROOT"

    copy_executable "$build_dir" "${executables[@]}"
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
