#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${ROOT}/_build_logs"
SUMMARY="${LOG_DIR}/summary.txt"

CONTINUE_ON_FAIL="${CONTINUE_ON_FAIL:-1}"   # 1: continue; 0: stop on first failure

mkdir -p "${LOG_DIR}"
: > "${SUMMARY}"

run_one_phase() {
  local bench_dir="$1"
  local bench_name="$2"
  local phase="$3"        # "static" or "default"
  local log_file="$4"

  echo "[build] ${bench_name} -> ${phase}"
  (
    cd "${bench_dir}"
    export BASH_XTRACEFD=  # harmless if unused

    if [[ "${phase}" == "static" ]]; then
      ./build.sh static
    else
      ./build.sh
    fi
  ) >"${log_file}" 2>&1
}

run_one() {
  local bench_dir="$1"
  local bench_name
  bench_name="$(basename "${bench_dir}")"

  if [[ ! -x "${bench_dir}/build.sh" ]]; then
    echo "[skip] ${bench_name} (no build.sh or not executable)" | tee -a "${SUMMARY}"
    return 0
  fi

  local log_static="${LOG_DIR}/${bench_name}.static.log"
  local log_default="${LOG_DIR}/${bench_name}.default.log"

  # Phase 1: static
  if ! run_one_phase "${bench_dir}" "${bench_name}" "static" "${log_static}"; then
    echo "[fail] ${bench_name} (static)  (see ${log_static})" | tee -a "${SUMMARY}"
    if [[ "${CONTINUE_ON_FAIL}" == "0" ]]; then exit 1; fi
    return 1
  fi

  # Phase 2: default (no args)
  if ! run_one_phase "${bench_dir}" "${bench_name}" "default" "${log_default}"; then
    echo "[fail] ${bench_name} (default) (see ${log_default})" | tee -a "${SUMMARY}"
    if [[ "${CONTINUE_ON_FAIL}" == "0" ]]; then exit 1; fi
    return 1
  fi

  echo "[ok]   ${bench_name} (static + default)" | tee -a "${SUMMARY}"
  return 0
}

main() {
  echo "[info] root: ${ROOT}"
  echo "[info] logs: ${LOG_DIR}"
  echo "[info] continue_on_fail: ${CONTINUE_ON_FAIL}"
  echo "[info] phases: ./build.sh static  then  ./build.sh"
  echo

  mapfile -t benches < <(find "${ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)

  local failed=0
  for d in "${benches[@]}"; do
    [[ "$(basename "$d")" == "__scripts__" ]] && continue
    [[ "$(basename "$d")" == "_build_logs" ]] && continue

    if [[ -f "${d}/build.sh" ]]; then
      if ! run_one "${d}"; then
        failed=$((failed + 1))
      fi
    fi
  done

  echo
  echo "========================================"
  echo "Build summary (static + default)"
  echo "========================================"
  cat "${SUMMARY}"
  echo "========================================"

  if [[ "${failed}" -ne 0 ]]; then
    echo "[done] failures: ${failed}"
    exit 2
  fi

  echo "[done] all builds succeeded"
}

main "$@"
