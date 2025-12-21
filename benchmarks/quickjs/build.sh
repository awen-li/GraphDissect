#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="quickjs"

Action="$1"
executables=("qjs" "qjsc")

# load library
source ../__scripts__/base.sh

ensure_makefile() 
{
    if [ ! -f "$target/Makefile" ]; then
        echo "[quickjs] ERROR: Makefile missing in $target"
        exit 1
    fi
}

initialize() 
{
    if [ -d "$target" ]; then
        rm -rf $target
    fi
    git clone --depth 1 https://github.com/bellard/quickjs.git "$target"

    ensure_makefile
}

wllvm_compile() 
{
    # compiler only
    export CC="wllvm"
    export CXX="wllvm++"

    # add your analysis-friendly flags via environment,
    # QuickJS will append its own -g, DEFINES, etc.
    COMMON_FLAGS="-pg -g -O2 -save-temps=obj \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0 \
                  -w"

    export CFLAGS="$CFLAGS $COMMON_FLAGS"
    export CXXFLAGS="$CXXFLAGS $COMMON_FLAGS"

    (
        cd "$target"
        make clean || true
        # CC on the command line overrides CC=$(CROSS_PREFIX)clang/gcc in the Makefile
        make -j8 CC="$CC" LDFLAGS="-pg" qjs qjsc
    )

    handle_executable "$target" "${executables[@]}"
}

hfuzz_compile() 
{
    # compiler only
    export CC="hfuzz-clang"
    export CXX="hfuzz-clang++"

    # function coverage instrumentation for honggfuzz
    COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard \
                  -finstrument-functions"

    export CFLAGS="$CFLAGS $COMMON_FLAGS"
    export CXXFLAGS="$CXXFLAGS $COMMON_FLAGS"
    export LDFLAGS="$LDFLAGS $COMMON_FLAGS"
    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    (
        cd "$target"
        make clean || true
        make -j8 CC="$CC" qjs qjsc
    )

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
