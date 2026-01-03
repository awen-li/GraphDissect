

export ROOT=`pwd`
export target=xpdf-4.06

Action=$1
executables=("pdfdetach" "pdfinfo" "pdftops")

# load library
source ../__scripts__/base.sh

function initialize ()
{
	export PKG_CONFIG_PATH=/root/anaconda3/lib/pkgconfig:$PKG_CONFIG_PATH

	if [ ! -d "$target" ]; then
		tar -xvf $target.tar.gz 
	fi

	export CPLUS_INCLUDE_PATH="/usr/include/c++/11:/usr/include/x86_64-linux-gnu/c++/11:${CPLUS_INCLUDE_PATH}"

	export LIBRARY_PATH=/usr/lib/gcc/x86_64-linux-gnu/11:$LIBRARY_PATH
	export LD_LIBRARY_PATH=/usr/lib/gcc/x86_64-linux-gnu/11:$LD_LIBRARY_PATH
}

function wllvm_compile ()
{
	export CC="wllvm -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
	export CXX="wllvm++ -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

	if [ -d "build" ]; then rm -rf build; fi
	mkdir build && cd build
	
	cmake ../$target
	make -j4
	cd -
	
	handle_executable build/xpdf $executables
}

function hfuzz_compile ()
{
	export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
	export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

	if [ -d "build" ]; then rm -rf build; fi
	mkdir build && cd build

	cmake ../$target
	make -j4
	cd -

	copy_executable build/xpdf $executables
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

