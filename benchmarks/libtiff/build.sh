#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="libtiff"
executables=("tiff2bw" "tiff2pdf" "tiffinfo")

Action=$1

source ../__scripts__/base.sh

ensure_configure() {
    if [ -x "$target/autogen.sh" ]; then
	( cd "$target" && ./autogen.sh )
    fi
    
    if [ ! -f "$target/configure" ]; then
	echo "[libtiff] ERROR:  configure script missing in $target"
	exit 1
    fi
}

initialize() {
	export ACLOCAL_PATH=/usr/share/aclocal:${ACLOCAL_PATH}
	if [ ! -d "$target" ]; then
        echo "[libtiff] cloning upstream repo..."
        git clone --depth 1 https://gitlab.com/libtiff/libtiff.git "$target"
    fi
    ensure_configure

    GPP_VER="$(g++ -dumpversion || g++ -dumpfullversion 2>/dev/null || echo 12)"
    export CPLUS_INCLUDE_PATH="/usr/include/c++/${GPP_VER}:/usr/include/x86_64-linux-gnu/c++/${GPP_VER}:${CPLUS_INCLUDE_PATH:-}"
    export LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:${LIBRARY_PATH:-}"
}


wllvm_compile() {

    export LLVM_COMPILER=clang

    export CC="wllvm"
    export CXX="wllvm++"

    COMMON_FLAGS="-g -O2 -pg\
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0"

    export CFLAGS="${COMMON_FLAGS}"
    export CXXFLAGS="${COMMON_FLAGS}"

    cd $target
    make distclean >/dev/null 2>&1 || true
    ./configure \
        --enable-static \
        --disable-shared \
        --disable-dependency-tracking
    make -j8
    cd $ROOT

    handle_executable "$target/tools" "${executables[@]}"
}


hfuzz_compile() {

    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    export CFLAGS="-g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export CXXFLAGS="-g -O2 -fsanitize-coverage=trace-pc-guard -finstrument-functions"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}

    cd "$target"
    make distclean >/dev/null 2>&1 || true
    ./configure \
        --enable-static \
        --disable-shared \
        --disable-dependency-tracking
    make -j8
    cd "$ROOT"

    copy_executable "$target/tools" "${executables[@]}"
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
