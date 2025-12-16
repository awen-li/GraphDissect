
BASE_DIR=`pwd`

Action=$1

#dependences
apt install libjson-c-dev

if [ "$Action" == "clean" ]; then
	cd $BASE_DIR/honggfuzz && make clean

	rm -rf $BASE_DIR/fuzzpilot/build
	rm -rf $BASE_DIR/fuzzpilot/FuzzPilot.egg*

	cd $BASE_DIR/SVF
	if [ -d "Release-build" ]; then rm -rf Release-build z3.obj; fi

	cd $BASE_DIR/mfuzz && rm -rf build

	exit 0
fi


# 1. build honggfuzz
cd $BASE_DIR/honggfuzz && make


# 2. build SVF
cd $BASE_DIR/SVF
if [ -d "Release-build" ]; then
    cd Release-build && make 
else
	source ./build.sh
fi

# 3. build mfuzz
cd $BASE_DIR/mfuzz && ./build.sh && cd $BASE_DIR

