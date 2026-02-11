#!/usr/bin/env bash
set -u
set -o pipefail 2>/dev/null || true

# Dynamic tmux-based fuzz scheduler for fuzzpilot benchmarks.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BENCH_DIR="${BASE_DIR}/benchmarks"
LOGS_DIR="${SCRIPT_DIR}/logs"
EXEC_COMPLETION_LOG_FILE="${LOGS_DIR}/fuzz_executions.log"

SESSION_PREFIX="dgs_exec_"
CONCURRENCY_DEFAULT=8
LAUNCHED_COUNT=0
SKIPPED_COUNT=0

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
  ["xpdf"]="pdfdetach pdfinfo pdftops"
  ["libxml2"]="xmllint"
  ["jq"]="jq"

  # toolchain_and_binary_utilities
  ["binutils"]="objdump readelf addr2line"
  ["cppcheck"]="cppcheck"
  ["libdwarf"]="dwarfdump"

  # language_runtimes_and_interpreters
  ["cpython3"]="python"
  ["quickjs"]="qjs qjsc"
  ["lua"]="lua"

  # archive_and_compression
  ["libarchive"]="bsdtar bsdunzip"
  ["upx"]="upx"
  ["xz"]="xz"

  # database_and_storage
  ["hdf5"]="h5dump h5ls h5repack"
  ["netcdf"]="ncdump ncgen nccopy"
  ["leveldb"]="leveldbutil"
)


human_duration() {
  local sec="$1"
  if ! [[ "$sec" =~ ^[0-9]+$ ]]; then
    sec=0
  fi
  printf '%02d:%02d:%02d\n' "$((sec/3600))" "$(((sec%3600)/60))" "$((sec%60))"
}

log_header_once() {
  mkdir -p "$(dirname "${EXEC_COMPLETION_LOG_FILE}")"
  if [[ ! -f "${EXEC_COMPLETION_LOG_FILE}" ]]; then
    local ts
    ts="$(date '+%F %T')"
    {
      echo "# Fuzz executions log - ${ts}"
      echo "# Format: <end_time> | <benchmark/executable> | seconds=<sec> | human=<HH:MM:SS>"
    } > "${EXEC_COMPLETION_LOG_FILE}"
  fi
}

log_completion() {
  local bench="$1"
  local exe="$2"
  local seconds="$3"

  log_header_once
  local end_ts human
  end_ts="$(date '+%F %T')"
  human="$(human_duration "${seconds}")"
  local line="${end_ts} | ${bench}/${exe} | seconds=${seconds} | human=${human}"
  echo "${line}" | tee -a "${EXEC_COMPLETION_LOG_FILE}"
}

tmux_has_session() {
  local name="$1"
  if tmux has-session -t "${name}" 2>/dev/null; then
    return 0
  fi
  return 1
}

tmux_new_session() {
  local name="$1"
  local cwd="$2"
  local cmd="$3"
  tmux new-session -d -s "${name}" -c "${cwd}" bash -lc "${cmd}"
}

CONCURRENCY="${CONCURRENCY_DEFAULT}"
FUZZ_FLAGS=()
bench_executables=()

print_usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --concurrency N          Max number of concurrent tmux sessions (default: ${CONCURRENCY_DEFAULT})
  -m, --max_time SECONDS   Pass -m SECONDS to fuzzpilot (overall max fuzzing time)
                           Pass --disable-edge-drift to fuzzpilot
  -e, --execs EXE_NAME     Only run fuzzing for executables matching EXE_NAME (can specify multiple)
  -h, --help               Show this help

EOF
}

parse_args() {
  local arg
  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "${arg}" in
      --concurrency)
        if [[ $# -lt 2 ]]; then
          echo "[!] --concurrency requires an argument" >&2
          exit 1
        fi
        CONCURRENCY="$2"
        shift 2
        ;;
      -m|--max_time)
        if [[ $# -lt 2 ]]; then
          echo "[!] -m/--max_time requires an argument (seconds)" >&2
          exit 1
        fi
        FUZZ_FLAGS+=("-m" "$2")
        shift 2
        ;;
      -e|--execs)
        if [[ $# -lt 2 || -z "${2:-}" ]]; then
          echo "[!] -e/--execs requires an argument (executable name)" >&2
          exit 1
        fi
        bench_executables+=("$2")
        shift 2
        ;;
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        echo "[!] Unknown argument: ${arg}" >&2
        print_usage
        exit 1
        ;;
    esac
  done

  if ! [[ "${CONCURRENCY}" =~ ^[0-9]+$ ]] || [[ "${CONCURRENCY}" -le 0 ]]; then
    echo "[!] Invalid concurrency: ${CONCURRENCY} (must be positive integer)" >&2
    exit 1
  fi
}

declare -A START_TIMES
declare -A LABELS
SESSION_LIST=()

start_exec() {
  local bench="$1"
  local exe="$2"

  local exec_dir="${BENCH_DIR}/${bench}/${exe}"
  if [[ ! -d "${exec_dir}" ]]; then
    echo "Skip (missing dir): ${bench}/${exe} -> ${exec_dir}"
    ((SKIPPED_COUNT++))
    return 1
  fi

  local sess_name="${SESSION_PREFIX}${bench}_${exe}"

  if tmux_has_session "${sess_name}"; then
    echo "Session already exists, skipping: ${sess_name}"
    return 1
  fi

  local cmd="mfuzz"
  if [[ ${#FUZZ_FLAGS[@]} -gt 0 ]]; then
    cmd+=" ${FUZZ_FLAGS[*]}"
  fi
  cmd+=" -b ."
  #cmd+=" -b .; echo '[DONE]' ; exec bash"

  echo "[*] Starting: ${bench}/${exe} (session: ${sess_name})"
  if ! tmux_new_session "${sess_name}" "${exec_dir}" "${cmd}"; then
    echo "[!] Failed to start tmux session for ${bench}/${exe}" >&2
    ((SKIPPED_COUNT++))
    return 1
  fi

  local now
  now="$(date +%s)"
  START_TIMES["${sess_name}"]="${now}"
  LABELS["${sess_name}"]="${bench}/${exe}"
  SESSION_LIST+=("${sess_name}")
  ((LAUNCHED_COUNT++))
  return 0
}

active_count() {
  local count=0
  local name
  for name in "${SESSION_LIST[@]}"; do
    if tmux_has_session "${name}"; then
      ((count++))
    fi
  done
  echo "${count}"
}

prune_finished() {
  local name
  local now start_ts label runtime bench exe

  now="$(date +%s)"
  for name in "${SESSION_LIST[@]}"; do
    if tmux_has_session "${name}"; then
      continue
    fi
    start_ts="${START_TIMES[${name}]-}"
    label="${LABELS[${name}]-}"
    if [[ -z "${start_ts}" || -z "${label}" ]]; then
      continue
    fi
    runtime=$(( now - start_ts ))
    if (( runtime < 0 )); then
      runtime=0
    fi
    bench="${label%%/*}"
    exe="${label##*/}"
    log_completion "${bench}" "${exe}" "${runtime}"
    unset "START_TIMES[${name}]"
    unset "LABELS[${name}]"
  done
}

has_flag() {
  local needle="$1"
  local x
  for x in "${FUZZ_FLAGS[@]}"; do
    if [[ "$x" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}


cleanup_on_signal() {
  echo
  echo "[!] Signal caught; logging runtimes and killing tmux sessions..."

  local now name start_ts label runtime bench exe
  now="$(date +%s)"

  for name in "${SESSION_LIST[@]}"; do
    if ! tmux_has_session "${name}"; then
      continue
    fi
    start_ts="${START_TIMES[${name}]-}"
    label="${LABELS[${name}]-}"
    if [[ -n "${start_ts}" && -n "${label}" ]]; then
      runtime=$(( now - start_ts ))
      if (( runtime < 0 )); then
        runtime=0
      fi
      bench="${label%%/*}"
      exe="${label##*/}"
      log_completion "${bench}" "${exe}" "${runtime}"
    fi
    tmux kill-session -t "${name}" 2>/dev/null || true
  done

  # Also ensure no stray honggfuzz processes remain
  pkill -TERM -f honggfuzz >/dev/null 2>&1 || true
  sleep 1
  pkill -KILL -f honggfuzz >/dev/null 2>&1 || true

  exit 130
}

is_in_bench_executables() {
  # Found by default if array is unset or empty
  if [[ ${#bench_executables[@]} -eq 0 ]]; then
    return 1
  fi

  local target="${1:-}"
  local x
  for x in "${bench_executables[@]}"; do
    [[ "$x" == "$target" ]] && return 1
  done

  return 0
}


init_queue() {
  local -a queue=()

  # Prioritize a few benches first (edit as you like)
  local -a first_benches=("libxml2" "snort3" "netcdf" "git" "xz" "upx" "leveldb" 
                          "file" "jq" "cppcheck" "unbound" "cpython3")

  local b e
  for b in "${first_benches[@]}"; do
    if [[ -n "${BENCHMARK_EXECUTABLES[$b]:-}" ]]; then
      for e in ${BENCHMARK_EXECUTABLES[$b]}; do
        if ! is_in_bench_executables "${e}"; then
          continue
        fi
        queue+=("${b}:${e}")
      done
    else
      echo "[!] Warning: benchmark '$b' not found in BENCHMARK_EXECUTABLES" >&2
    fi
  done

  # The rest (edit ordering as desired)
  local -a rest_benches=(
    "binutils" "xpdf" "ffmpeg" "libtiff" "libpng"
    "quickjs" "hdf5"  "sleuthkit" "libdwarf"
    "lua" "libarchive"  "http-parser")

  for b in "${rest_benches[@]}"; do

    # skip benches already in first_benches to avoid duplicates
    case " ${first_benches[*]} " in
      *" $b "*) continue ;;
    esac

    if [[ -n "${BENCHMARK_EXECUTABLES[$b]:-}" ]]; then
      for e in ${BENCHMARK_EXECUTABLES[$b]}; do
        if ! is_in_bench_executables "${e}"; then
          continue
        fi
        queue+=("${b}:${e}")
      done
    else
      echo "[!] Warning: benchmark '$b' not found in BENCHMARK_EXECUTABLES" >&2
    fi
  done

  if ((${#queue[@]} == 0)); then
    echo "[!] No tasks to run (queue is empty). Check BENCHMARK_EXECUTABLES mapping." >&2
    exit 1
  fi

  # return queue via stdout (one per line) OR export a global
  printf '%s\n' "${queue[@]}"
}


main() {
  parse_args "$@"

  if ! command -v tmux >/dev/null 2>&1; then
    echo "[!] tmux is required but not found in PATH" >&2
    exit 1
  fi

  if ! [[ -d "${BENCH_DIR}" ]]; then
    echo "[!] Benchmarks directory not found: ${BENCH_DIR}" >&2
    exit 1
  fi

  trap cleanup_on_signal INT TERM

  local -a queue=()
  mapfile -t queue < <(init_queue)

  echo "[*] Total tasks: ${#queue[@]} (concurrency=${CONCURRENCY})"

  local idx=0
  local total="${#queue[@]}"

  while :; do
    prune_finished || true

    local current
    current="$(active_count 2>/dev/null || echo 0)"
    # ensure it's an integer
    [[ "$current" =~ ^[0-9]+$ ]] || current=0

    while (( current < CONCURRENCY && idx < total )); do
      local item="${queue[$idx]}"
      ((idx++))

      local b="${item%%:*}"
      local e="${item##*:}"

      if start_exec "$b" "$e"; then
        ((current++))
      fi
    done

    if (( idx >= total )); then
      current="$(active_count 2>/dev/null || echo 0)"
      [[ "$current" =~ ^[0-9]+$ ]] || current=0

      if (( current == 0 )); then
        echo "[*] All fuzzing tasks completed."
        echo "[*] Launched sessions: ${LAUNCHED_COUNT}, skipped: ${SKIPPED_COUNT}"
        echo "[*] Execution summary logged at: ${EXEC_COMPLETION_LOG_FILE}"
        break
      fi
    fi

    sleep 3
  done
}


main "$@"




