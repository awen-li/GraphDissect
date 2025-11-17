

export ROOT=`pwd`
export target=binutils-gdb

Action=$1
executables=("objdump" "readelf" "addr2line" "nm-new" "ranlib" "strings" "strip-new" "elfedit")

# load library
source ../__scripts__/base.sh 


function initialize ()
{
	export PKG_CONFIG_PATH=/root/anaconda3/lib/pkgconfig:$PKG_CONFIG_PATH

	apt-get install texinfo
	
	if [ ! -d "$target" ]; then
		git clone https://github.com/bminor/binutils-gdb
	fi

	cd $target/libiberty

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
	export CC=wllvm
	export CXX=wllvm++

	COMMON_FLAGS="-pg -g -O2 -save-temps=obj \
				-fno-discard-value-names \
				-fno-inline-functions \
				-fno-inline-functions-called-once \
				-mllvm -inline-threshold=0 \
				-w \
				-D_GNU_SOURCE -DLONG_MIN=-9223372036854775808"

	export CFLAGS="$COMMON_FLAGS"
	export CXXFLAGS="$COMMON_FLAGS"
	export LDFLAGS="-static"
	
	if [ -d "build" ]; then
		rm -rf build
	fi
	mkdir build

	cd build
	../$target/configure --disable-gprofng --disable-nls --disable-gdb --disable-gdbserver --disable-sim
	make -j4
	cd ..
}

function hfuzz_compile ()
{
	export CC=hfuzz-clang
	export CXX=hfuzz-clang++

	export COMMON_FLAGS="-fsanitize-coverage=trace-pc-guard -finstrument-functions -w \
						-D_GNU_SOURCE -DLONG_MIN=-9223372036854775808"

	export CFLAGS="$COMMON_FLAGS"
	export CXXFLAGS="-std=c++17 $COMMON_FLAGS"

	if [ -d "build" ]; then
		rm -rf build
	fi
	mkdir build

	cd build
	../$target/configure --disable-gprofng --disable-nls --disable-gdb --disable-gdbserver --disable-sim

	make -j4
	cd -
}


if [ "$Action" == "clean" ]; then
	clean
	exit 0
fi


cd $ROOT
compile



