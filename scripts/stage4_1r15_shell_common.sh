#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R15_PROJECT_DIR="${STAGE4_1R15_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R15_CONFIG="${STAGE4_1R15_CONFIG:-${STAGE4_1R15_PROJECT_DIR}/configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json}"
STAGE4_1R15_PYTHON="${STAGE4_1R15_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R15_WORKERS="${STAGE4_1R15_WORKERS:-128}"
STAGE4_1R15_BACKEND="${STAGE4_1R15_BACKEND:-ray}"
STAGE4_1R15_COMMAND="${STAGE4_1R15_COMMAND:-all}"
STAGE4_1R15_RESUME="${STAGE4_1R15_RESUME:-0}"
STAGE4_1R15_OUTPUT_ROOT="${STAGE4_1R15_OUTPUT_ROOT:-${STAGE4_1R15_PROJECT_DIR}/stage4_1r15_runs}"
STAGE4_1R15_TSC_WORKSPACE_ROOT="${STAGE4_1R15_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R15_TSC_RUN_ROOT="${STAGE4_1R15_TSC_RUN_ROOT:-${STAGE4_1R15_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r15_${UID:-0}}"

stage4_1r15_source_r14_complete() {
  local source="$1"
  local required
  for required in \
    stage4_1r14_manifest.json \
    stage4_1r14_state.json \
    stage4_1r14_config.resolved.json \
    stage4_1r14_analysis/stage4_1r14_verdict.json \
    stage4_1r14_analysis/stage4_1r14_summary.json \
    stage4_1r14_source_audit/summary.json \
    stage4_1r14_oracle_development/summary.json \
    stage4_1r14_oracle_development/results.json \
    stage4_1r14_oracle_development/results.csv; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  local raw_count
  raw_count="$(find "${source}/stage4_1r14_oracle_development/raw" -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l)"
  [[ "${raw_count}" -eq 24 ]]
}

stage4_1r15_find_source_r14() {
  local explicit="${STAGE4_1R15_SOURCE_STAGE4_1R14_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || { echo "ERROR: explicit R14 source directory missing: ${explicit}" >&2; return 1; }
    stage4_1r15_source_r14_complete "${explicit}" || { echo "ERROR: explicit R14 source is incomplete or raw coverage is not 24/24: ${explicit}" >&2; return 1; }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R15_PROJECT_DIR}/stage4_1r14_runs/latest_stage4_1r14_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" ]] && stage4_1r15_source_r14_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if stage4_1r15_source_r14_complete "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R15_PROJECT_DIR}/stage4_1r14_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r15_new_run_dir() {
  mkdir -p "${STAGE4_1R15_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R15_OUTPUT_ROOT}/stage4_1r15_bounded_early_braking_local_response_identification_${stamp}"
}

stage4_1r15_validate_common() {
  [[ -x "${STAGE4_1R15_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R15_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R15_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R15_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R15_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_1R15_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_1R15_BACKEND}" == "ray" || "${STAGE4_1R15_BACKEND}" == "serial" ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R15_RESUME}" == "0" || "${STAGE4_1R15_RESUME}" == "1" ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R15_COMMAND}" in all|audit|model|probes) ;; *) echo "ERROR: invalid command ${STAGE4_1R15_COMMAND}" >&2; return 1 ;; esac
}

stage4_1r15_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R15_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R15_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R15_WORKERS STAGE4_1R15_TSC_WORKSPACE_ROOT STAGE4_1R15_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_1R15_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_1R15_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R15_TSC_RUN_ROOT}"
}
