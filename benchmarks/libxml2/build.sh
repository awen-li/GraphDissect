

export ROOT=`pwd`
export target=libxml2

Action=$1
executables=("xmllint")

# load library
source ../__scripts__/base.sh 


ensure_configure() {
    # Generate ./configure if we cloned from git and only have autogen.sh
    if [ ! -f "$target/configure" ] && [ -x "$target/autogen.sh" ]; then
        echo "[libxml2] configure not found, running autogen.sh..."
        ( cd "$target" && NOCONFIGURE=1 ./autogen.sh )
    fi

    if [ ! -f "$target/configure" ]; then
        echo "[libxml2] ERROR: configure script still missing in $target"
        exit 1
    fi
}

initialize() {
    export PKG_CONFIG_PATH="/root/anaconda3/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
    export ACLOCAL_PATH=/usr/share/aclocal:${ACLOCAL_PATH}
    export PATH=/usr/local/bin:$PATH
    if [ ! -d "$target" ]; then
        echo "[libxml2] cloning upstream repo..."
        git clone --depth 1 https://gitlab.gnome.org/GNOME/libxml2.git "$target"
    fi

    ensure_configure
}

function wllvm_compile ()
{
	export CC="wllvm -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
	export CXX="wllvm++ -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

    # 1) Clean the *source* tree if it was configured before
    if [ -d "$target" ]; then
        ( cd "$target" && make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true )
    fi

    # 2) Fresh out-of-tree build
	build_dir="build-wllvm"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd $build_dir
    ../$target/configure --enable-shared=no
    make -j4
    cd -

	handle_executable $build_dir $executables
}

function hfuzz_compile ()
{
	export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
	export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

	export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

    # 1) Clean the *source* tree if it was configured before
    if [ -d "$target" ]; then
        ( cd "$target" && make distclean >/dev/null 2>&1 || make clean >/dev/null 2>&1 || true )
    fi

    # 2) Fresh out-of-tree build
	build_dir="build-hfuzz"
    rm -rf "$build_dir" && mkdir "$build_dir"

    cd $build_dir
    ../$target/configure --enable-shared=no
    make -j4
    cd -

	copy_executable $build_dir $executables
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

cd $ROOT
compile



