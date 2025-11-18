#!/bin/bash

#export ROOT=`pwd`                        : the root directory the benchmark  
#export target=sablot-1.0.3               : the source of the benchmark
export FUNC_ADDR_MAP="function_addr.map"  

#
# handle_executable path [executable], e.g., andle_executable ./libxml ("xmlline" "parser")
#
function handle_executable() 
{
    executable_path=$1
    executables=$2


    #if [ ! -d "seeds" ]; then
	#	mkdir seeds
	#	tar -xvf seeds.tar -C seeds
	#fi

    for exe in "${executables[@]}"; do
        executable=$exe
        benchpath=$exe

        if [ ! -d "$benchpath" ]; then
            mkdir "$benchpath"
        fi
        
        # Generate bc
		extract-bc $executable_path/$executable && cp $executable_path/$executable.bc ./
		#cp $executable_path/$executable $benchpath/pg_$executable
		#cp $executable_path/$executable $benchpath/$executable

        # Whole-program callgraph construction
        #if [ ! -f "$benchpath/callgraph_final.dot" ]; then
			#export ONLY_CG="true"
		    #wpa -fspta  -dump-callgraph $executable.bc
		    #mv callgraph_final.dot "$benchpath/"
		#fi
        #rm *.bc

		# Copy initial seed directory
        #cp -rf seeds "$benchpath/"

		# generate driver
		#python -m driverscope $benchpath --binary $benchpath/$executable
    done
}

function copy_executable ()
{
    executable_path=$1
    executables=$2

	for exe in "${executables[@]}"; do
        executable=$exe
        benchpath=$exe

		if [ ! -d "$benchpath" ]; then
			mkdir $benchpath
		fi

		cp $executable_path/$executable $benchpath
		nm $benchpath/$executable > "$benchpath/$FUNC_ADDR_MAP"

		# Generate function address to ID mappingAdd commentMore actions
	done
}

function copy_driver () {
    executables=$1

    for benchpath in "${executables[@]}"; do
        executable="$(basename "$benchpath")"
        executable_path="$(realpath "$benchpath")"/$executable

        driver_dir=$benchpath
        cd "$driver_dir" || { echo "Failed to cd to $driver_dir"; continue; }

        for drv in drivers/*/; do
            if [ -d "$drv" ]; then
                ln -sf "$executable_path" "$drv/$executable" || echo "Failed to link $executable_path to $drv"
            fi
        done

        cd ..
    done
}


function clean_driver ()
{
    executables=$1

	for exe in "${executables[@]}"; do
        executable=$exe
        benchpath=$exe

		cd $benchpath
		for drv in drivers/*/; do
			if [ -d "$drv" ]; then
				unlink $drv/$executable
			fi
		done
		cd -
	done
}


function clean()
{
    rm -rf $target
	rm -rf *.bc

    clean_driver
}


function compile ()
{
	initialize

	if [ "$Action" == "all" ]; then

		# Compile with wllvm for SVF/static analysis
		wllvm_compile

		# Compile for fuzzing
		hfuzz_compile	

		$copy_driver $executables
		
	elif [ "$Action" == "static" ]; then
		# Only compile for static analysis
		wllvm_compile

	else
		# Default: compile for fuzzing only
		hfuzz_compile

		#copy_driver $executables
	fi
}

