#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./count_funcs_and_drivers.sh /path/to/benchmarks
#
# Expected layout:
#   <BENCH_ROOT>/<benchmark>/<executable>/faddr_id.map
#   <BENCH_ROOT>/<benchmark>/<executable>/drivers/<driver_dir>/

BENCH_ROOT="${1:-.}"
if [[ -z "${BENCH_ROOT}" || ! -d "${BENCH_ROOT}" ]]; then
  echo "Usage: $0 /path/to/benchmarks_root" >&2
  exit 1
fi

declare -A BENCHMARK_EXECUTABLES=(
  # network_and_protocols
  ["snort3"]="snort snort2lua"
  ["unbound"]="unbound-checkconf"
  ["http-parser"]="parsertrace url_parser"

  # media_processing
  ["ffmpeg"]="ffmpeg ffprobe"
  ["libtiff"]="tiff2bw tiffinfo tiff2pdf"
  ["libpng"]="pngfix pngimage pngvalid"

  # metadata_and_system_utilities
  ["git"]="git"
  ["sleuthkit"]="istat img_stat tsk_recover"
  ["file"]="file"

  # parsing_and_document_processing
  ["xpdf"]="pdftotext pdfinfo pdftoppm"
  ["libxml2"]="xmllint"
  ["jq"]="jq"

  # toolchain_and_binary_utilities
  ["binutils"]="objdump readelf addr2line"
  ["cppcheck"]="cppcheck"
  ["libdwarf"]="dwarfdump"

  # language_runtimes_and_interpreters
  ["cpython"]="python"
  ["quickjs"]="qjs qjsc"
  ["lua"]="lua luac"

  # archive_and_compression
  ["libarchive"]="bsdtar bsdunzip"
  ["upx"]="upx"
  ["xz"]="xz"

  # database_and_storage
  ["hdf5"]="h5dump h5ls h5repack"
  ["netcdf"]="ncdump ncgen nccopy"
  ["leveldb"]="leveldbutil"
)

# CSV header
echo "benchmark,executable,exe_dir,function_count,driver_count,faddr_id_map_path,drivers_dir_path"

for bench in "${!BENCHMARK_EXECUTABLES[@]}"; do
  for exe in ${BENCHMARK_EXECUTABLES[$bench]}; do
    exe_dir="${BENCH_ROOT}/${bench}/${exe}"

    if [[ ! -d "${exe_dir}" ]]; then
      echo "Warning: Executable directory not found: ${exe_dir}" >&2
      continue
    fi

    # 1) Function count: count lines in faddr_id.map
    fid_map_file="${exe_dir}/faddr_id.map"
    if [[ ! -f "${fid_map_file}" ]]; then
      echo "Warning: faddr_id.map not found: ${fid_map_file}" >&2
      continue
    fi
    fmap_path="${fid_map_file}"
    func_cnt="$(wc -l < "${fid_map_file}" | tr -d '[:space:]')"

    # 2) Driver count: count immediate child directories under drivers/
    drivers_dir="${exe_dir}/drivers"
    if [[ ! -d "${drivers_dir}" ]]; then
      echo "Warning: Drivers directory not found: ${drivers_dir}" >&2
      continue
    fi

    # Count directories robustly (names with spaces ok)
    drv_cnt="$(
      find "${drivers_dir}" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null \
        | tr -cd '\0' | wc -c | tr -d '[:space:]'
    )"

    echo "${bench},${exe},${exe_dir},${func_cnt},${drv_cnt},${fmap_path},${drivers_dir}"
  done
done
