

export ROOT=`pwd`
export target=binutils-2.44

Action=$1
executables=("objdump" "readelf" "addr2line" "nm-new" "ranlib" "strings" "strip-new" "elfedit")

# load library
source ../__scripts__/base.sh 


function initialize ()
{
	export PKG_CONFIG_PATH=/root/anaconda3/lib/pkgconfig:$PKG_CONFIG_PATH
	
	if [ ! -d "$target" ]; then
		tar -xvf $target.tar.xz
	fi

	cd binutils-2.44/libiberty

	# Backup original file
	cp pex-unix.c pex-unix.c.bak

	# Inject headers at top of the original file
	{
		echo "#include <fcntl.h>"
		echo "#include <spawn.h>"
		cat pex-unix.c.bak
	} > pex-unix.c

	cd -
}

function wllvm_compile ()
{
	export CC="wllvm -pg -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
	export CXX="wllvm++ -pg -g -O2 -save-temps=obj -fno-discard-value-names -fno-inline-functions -fno-inline-functions-called-once -mllvm -inline-threshold=0 -w"
	export CPPFLAGS="-D_GNU_SOURCE -DLONG_MIN=-9223372036854775808"
	export LDFLAGS="-static"
	
	if [ -d "build" ]; then
		rm -rf build
	fi
	mkdir build

	cd build
	../$target/configure
	make -j4
	cd ..

	handle_executable build/binutils $executables
}

function hfuzz_compile ()
{
	export CC="hfuzz-clang -fsanitize-coverage=trace-pc-guard -finstrument-functions"
	export CXX="hfuzz-clang++ -fsanitize-coverage=trace-pc-guard -finstrument-functions"

	if [ -d "build" ]; then
		rm -rf build
	fi
	mkdir build

	cd build
	../$target/configure
	make -j4
	cd -

	copy_executable build/binutils $executables
}


if [ "$Action" == "clean" ]; then
	clean
	exit 0
fi


cd $ROOT
compile



