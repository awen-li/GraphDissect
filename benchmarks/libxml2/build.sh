

export ROOT=`pwd`
export target=libxml2-2.13.0

Action=$1
executables=("xmllint")

# load library
source ../__scripts__/base.sh 


function initialize ()
{
	export PKG_CONFIG_PATH=/root/anaconda3/lib/pkgconfig:$PKG_CONFIG_PATH
	
	if [ ! -d "$target" ]; then
		tar -xvf $target.tar.xz
	fi
}

function wllvm_compile ()
{
	export CC="wllvm -pg -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
	export CXX="wllvm++ -pg -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"

	cd $target
	./configure --enable-shared=no
	make
	cd -

	handle_executable $target $executables
}

function hfuzz_compile ()
{
	export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
	export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

	export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

	cd $target
	./configure --enable-shared=no
	bear make -j$(nproc)
	cd -

	copy_executable $target $executables
}


if [ "$Action" == "clean" ]; then
	clean
	exit 0
fi


cd $ROOT
compile



