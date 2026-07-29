#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R15B_PROJECT_DIR="${STAGE4_1R15B_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R15B_CONFIG="${STAGE4_1R15B_CONFIG:-${STAGE4_1R15B_PROJECT_DIR}/configs/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json}"
STAGE4_1R15B_PYTHON="${STAGE4_1R15B_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R15B_WORKERS="${STAGE4_1R15B_WORKERS:-128}"
STAGE4_1R15B_BACKEND="${STAGE4_1R15B_BACKEND:-ray}"
STAGE4_1R15B_COMMAND="${STAGE4_1R15B_COMMAND:-all}"
STAGE4_1R15B_RESUME="${STAGE4_1R15B_RESUME:-0}"
STAGE4_1R15B_OUTPUT_ROOT="${STAGE4_1R15B_OUTPUT_ROOT:-${STAGE4_1R15B_PROJECT_DIR}/stage4_1r15b_runs}"
STAGE4_1R15B_TSC_WORKSPACE_ROOT="${STAGE4_1R15B_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R15B_TSC_RUN_ROOT="${STAGE4_1R15B_TSC_RUN_ROOT:-${STAGE4_1R15B_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r15b_${UID:-0}}"

stage4_1r15b_source_r15_complete() {
  local source="$1" required
  for required in \
    stage4_1r15_manifest.json \
    stage4_1r15_state.json \
    stage4_1r15_config.resolved.json \
    stage4_1r15_analysis/stage4_1r15_verdict.json \
    stage4_1r15_analysis/stage4_1r15_summary.json \
    stage4_1r15_source_audit/summary.json \
    stage4_1r15_local_response_model/models.json \
    stage4_1r15_local_response_model/summary.json \
    stage4_1r15_local_response_model/cross_validation.csv \
    stage4_1r15_bounded_probe_validation/summary.json \
    stage4_1r15_bounded_probe_validation/results.json \
    stage4_1r15_bounded_probe_validation/results.csv \
    stage4_1r15_bounded_probe_validation/central_symmetry.csv; do
    [[ -f "${source}/${required}" ]] || return 1
  done
  local raw_count
  raw_count="$(find "${source}/stage4_1r15_bounded_probe_validation/raw" -maxdepth 1 -type f -name '*.json.gz' 2>/dev/null | wc -l)"
  [[ "${raw_count}" -eq 32 ]]
}

stage4_1r15b_find_source_r15() {
  local explicit="${STAGE4_1R15B_SOURCE_STAGE4_1R15_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || { echo "ERROR: explicit R15 source directory missing: ${explicit}" >&2; return 1; }
    stage4_1r15b_source_r15_complete "${explicit}" || { echo "ERROR: explicit R15 source is incomplete or raw coverage is not 32/32: ${explicit}" >&2; return 1; }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R15B_PROJECT_DIR}/stage4_1r15_runs/latest_stage4_1r15_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" ]] && stage4_1r15b_source_r15_complete "${candidate}"; then printf '%s\n' "${candidate}"; return 0; fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if stage4_1r15b_source_r15_complete "${candidate}"; then printf '%s\n' "${candidate}"; return 0; fi
  done < <(find "${STAGE4_1R15B_PROJECT_DIR}/stage4_1r15_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r15_bounded_early_braking_local_response_identification_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r15b_new_run_dir() {
  mkdir -p "${STAGE4_1R15B_OUTPUT_ROOT}"
  local stamp; stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R15B_OUTPUT_ROOT}/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_${stamp}"
}

stage4_1r15b_validate_common() {
  [[ -x "${STAGE4_1R15B_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R15B_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R15B_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R15B_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R15B_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: workers must be positive" >&2; return 1; }
  [[ "${STAGE4_1R15B_BACKEND}" == ray || "${STAGE4_1R15B_BACKEND}" == serial ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R15B_RESUME}" == 0 || "${STAGE4_1R15B_RESUME}" == 1 ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R15B_COMMAND}" in all|audit|model|probes) ;; *) echo "ERROR: invalid command ${STAGE4_1R15B_COMMAND}" >&2; return 1 ;; esac
}

stage4_1r15b_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R15B_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R15B_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R15B_WORKERS STAGE4_1R15B_TSC_WORKSPACE_ROOT STAGE4_1R15B_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R15 R14 R13 R12 R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_1R15B_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_1R15B_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R15B_TSC_RUN_ROOT}"
}
