#!/usr/bin/env bash

export ROOT="$(pwd)"
export target="lua_src"

Action="$1"
executables=("lua")

# load library helpers (compile, clean, handle_executable, etc.)
source ../__scripts__/base.sh

ensure_makefile() 
{
    if [ ! -f "$target/makefile" ]; then
        echo "[lua] ERROR: makefile missing in $target/src"
        exit 1
    fi
}

initialize() 
{
    if [ ! -d "$target" ]; then
        echo "[lua] cloning upstream repo..."
        git clone --depth 1 https://github.com/lua/lua.git "$target"
    fi

    ensure_makefile
}

wllvm_compile() 
{
    CC="wllvm"
    COMMON_FLAGS="-pg -g -O2 -save-temps=obj \
                  -fno-discard-value-names \
                  -fno-inline-functions \
                  -fno-inline-functions-called-once \
                  -mllvm -inline-threshold=0 \
                  -w"

    (
        cd "$target"
        make clean
        # Lua's Makefile uses MYCFLAGS/MYLDFLAGS as extension hooks
        make -j8 CC="$CC" MYCFLAGS="$COMMON_FLAGS" MYLDFLAGS=""
    )

    # lua binary is in src/
    handle_executable "$target" "${executables[@]}"
}

hfuzz_compile() 
{
    CC="hfuzz-clang"
    HFUZZ_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions"

    export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    (
        cd "$target"
        make clean
        # instrument both compile & link
        make -j8 CC="$CC" MYCFLAGS="$HFUZZ_FLAGS" MYLDFLAGS="$HFUZZ_FLAGS"
    )
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
