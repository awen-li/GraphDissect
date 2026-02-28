#!/usr/bin/env bash
# copy_results_from_container.sh (HOST SIDE)
set -euo pipefail

CID="${1:-9cde386cfd76}"                        # container id/name
ROOT="${ROOT:-/root/GraphDissect/benchmarks}"    # inside container
OUT="${OUT:-./_fuzz_results_export}"             # on host

declare -A BENCHMARK_EXECUTABLES=(
  ["snort3"]="snort snort2lua"
  ["unbound"]="unbound-checkconf"
  ["http-parser"]="parsertrace url_parser"
  ["ffmpeg"]="ffmpeg ffprobe"
  ["libtiff"]="tiff2bw tiffinfo tiff2pdf"
  ["wavpack"]="wavpack wvunpack wvgain"
  ["git"]="git"
  ["sleuthkit"]="istat img_stat tsk_recover"
  ["file"]="file"
  ["xpdf"]="pdfdetach pdfinfo pdftops"
  ["libxml2"]="xmllint"
  ["jq"]="jq"
  ["binutils"]="objdump readelf addr2line"
  ["cppcheck"]="cppcheck"
  ["libdwarf"]="dwarfdump"
  ["cpython3"]="python"
  ["quickjs"]="qjs qjsc"
  ["lua"]="lua"
  ["libarchive"]="bsdtar bsdunzip"
  ["upx"]="upx"
  ["xz"]="xz"
  ["hdf5"]="h5dump h5ls h5repack"
  ["netcdf"]="ncdump ncgen nccopy"
  ["sqlite3"]="sqlite3"
)

ITEMS=(
  driver_runtimes
  drivers
  final_marked_callgraph.dot
  fuzz
  honggfuzz_profiling.txt
  mfuzz_drv_switch_cost.log
  mfuzz_f_coverage.log
)

mkdir -p "$OUT"

for bench in "${!BENCHMARK_EXECUTABLES[@]}"; do
  for exe in ${BENCHMARK_EXECUTABLES[$bench]}; do
    for item in "${ITEMS[@]}"; do
      src="$ROOT/$bench/$exe/$item"
      dst="$OUT/$bench/$exe"
      mkdir -p "$dst"
      # copy only if exists
      docker exec "$CID" bash -lc "test -e '$src'" 2>/dev/null && \
        docker cp "$CID:$src" "$dst/" || true
    done
  done
done

echo "[*] Done. Results at: $OUT"

