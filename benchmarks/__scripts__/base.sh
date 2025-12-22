#!/bin/bash

#export ROOT=`pwd`                        : the root directory the benchmark  
#export target=sablot-1.0.3               : the source of the benchmark
export FUNC_ADDR_MAP="function_addr.map"  

# Usage:
#   list_project_libs ./editcap
#   list_project_libs ./editcap /path/to/project_root
#
# If project_root is omitted, we use the directory of the executable.
list_project_libs() {
    local exe="$1"
    local exe_real
    local project_root project_root_real

    if [ -z "$exe" ]; then
        echo "Usage: list_project_libs <executable> [project_root]" >&2
        return 1
    fi

    if [ ! -x "$exe" ]; then
        echo "[error] '$exe' is not executable" >&2
        return 1
    fi

    exe_real="$(readlink -f "$exe")" || return 1

    if [ -n "${2-}" ]; then
        project_root="$2"
    else
        project_root="$(dirname "$exe_real")"
    fi
    project_root_real="$(readlink -f "$project_root")" || return 1

    echo "# Executable: $exe_real"
    echo "# Project root: $project_root_real"
    echo "# Local project DSOs:"

    ldd "$exe_real" | awk -v root="$project_root_real" '
        # Lines of the form: libfoo.so => /path/to/libfoo.so (0x...)
        $2 == "=>" && $3 ~ /^\// {
            cmd = "readlink -f " $3;
            real = "";
            if ((cmd | getline real) > 0) {
                close(cmd);
                if (index(real, root"/") == 1) {
                    printf "%s %s\n", $1, real;
                }
            } else {
                close(cmd);
            }
        }
    '
}

bc_total_size() {
    local total=0
    local size
    local binpath="$1"

    # Loop over sizes of all .bc files
    while read -r size _; do
        total=$(( total + size ))
    done < <(find "$binpath" -type f -name '*.bc' -printf '%s %p\n')

    echo "$total"
}

#
# handle_executable path [executable], e.g., andle_executable ./libxml ("xmlline" "parser")
#
function handle_executable() 
{
    executable_path=$1
    executables=$2
    is_so="${3:-}"

    if [ ! -d "seeds" ]; then
		mkdir seeds
		tar -xvf seeds.tar -C seeds
	fi

    for exe in "${executables[@]}"; do
        executable=$exe
        benchpath=$exe

        if [ ! -d "$benchpath" ]; then
            mkdir "$benchpath"
        fi
        
        # Generate bc for dependent libs
        if [ "$is_so" == "so" ]; then
	    list_project_libs "$executable_path/$executable" "$executable_path" \
		| grep -v '^#' \
		| while read -r lib_name lib_path; do
			echo "[*] extracting bc for $lib_name from $lib_path"
			extract-bc "$lib_path" && cp "${lib_path}.bc" $benchpath/
		  done 
        fi

        # Generate bc
	extract-bc $executable_path/$executable && cp $executable_path/$executable.bc $benchpath/
	cp $executable_path/$executable $benchpath/$executable

        # Whole-program callgraph construction (including dependent libs)
        if [ ! -f "$benchpath/callgraph_final.dot" ]; then
            export ONLY_CG="true"

            # Total size (bytes) of all .bc files under this benchmark
            total_bc_bytes=$(bc_total_size $benchpath)

            # Default PTA: flow-sensitive, Threshold: 200 MB (200 * 1024 * 1024 = 209715200 bytes)
            pta="-fspta"
            if [ "$total_bc_bytes" -gt 131072000 ]; then
                pta="-steens"
            fi

            echo "[cg] $benchpath: total .bc = $total_bc_bytes bytes, PTA = $pta"

            cd "$benchpath"
            wpa "$pta" -dump-callgraph ./*.bc
            cd -
        fi

		# Copy initial seed directory
        if [ -d "seeds" ]; then
            cp -rf seeds "$benchpath/"
        fi

		# generate driver
	 python -m gdriver $benchpath
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

		# Generate function address to ID mappingAdd commentMore actions
        python -m driverscope "$benchpath" --faddr --binary "$executable"
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


function clean()
{
    rm -rf $target

    executable_list=("$@")
    for exe in "${executable_list[@]}"; do
        benchpath=$exe
        if [ ! -d "$benchpath" ]; then
            continue
        fi

        echo "[*] Cleaning benchmark directory: $benchpath"
        # Remove per-binary artifacts
        rm -f  "$benchpath"/*.bc
        rm -f  "$benchpath"/*.dot
        rm -f  "$benchpath"/*.map

        # Remove generated subdirs
        rm -rf "$benchpath"/drivers
        rm -rf "$benchpath"/seeds

        # Remove stats
        rm -f  "$benchpath"/global_driver_stats.txt
        rm -f  "$benchpath"/per_driver_stats.txt

        # Remove instrumented binaries
        rm -f  "$benchpath"/pg_"$exe"
        rm -f  "$benchpath"/"$exe"
    done
}

driver_info() 
{
    local exe="$1"

    if [[ -z "$exe" ]]; then
        echo "[drivers] usage: driver_info <exe-dir-or-path>"
        return 1
    fi

    # Normalize: directory that contains drivers/
    local exe_dir="$exe"
    local drivers_dir="$exe_dir/drivers"

    if [[ ! -d "$exe_dir" ]]; then
        echo "[drivers] $exe: directory not found"
        return 1
    fi

    if [[ ! -d "$drivers_dir" ]]; then
        echo "[drivers] $exe: no drivers/ directory"
        return 0
    fi

    # Count only immediate subdirectories under drivers/
    local count
    count=$(find "$drivers_dir" -mindepth 1 -maxdepth 1 -type d | wc -l)
    printf "[drivers] %-*s  %4d\n" 16 "$exe" "$count"
}

show_driver_info()
{
    local executable_list=("$@")
    echo ""
    echo "========================================"
    echo " Driver Information Summary "
    echo "========================================"
    for exe in "${executable_list[@]}"; do
        driver_info "$exe"
    done
    echo "========================================"
    echo ""
}


function compile ()
{
	initialize

	if [ "$Action" == "all" ]; then

		# Compile with wllvm for SVF/static analysis
		wllvm_compile

		# Compile for fuzzing
		hfuzz_compile	

		copy_driver $executables
		
	elif [ "$Action" == "static" ]; then
		# Only compile for static analysis
		wllvm_compile

	else
		# Default: compile for fuzzing only
		hfuzz_compile

		copy_driver $executables
	fi

    show_driver_info $executables
}

