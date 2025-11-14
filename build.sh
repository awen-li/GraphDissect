
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

	cd $BASE_DIR/fuzzpilot/comlib && make clean

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

# 3. build driverscope
cd $BASE_DIR/fuzzpilot/comlib && make
cd $BASE_DIR/driverscope && pip install .

# 4. build FuzzPilot
cd $BASE_DIR/fuzzpilot && pip install .
