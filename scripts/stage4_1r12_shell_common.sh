#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R12_PROJECT_DIR="${STAGE4_1R12_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R12_CONFIG="${STAGE4_1R12_CONFIG:-${STAGE4_1R12_PROJECT_DIR}/configs/stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json}"
STAGE4_1R12_PYTHON="${STAGE4_1R12_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R12_WORKERS="${STAGE4_1R12_WORKERS:-128}"
STAGE4_1R12_BACKEND="${STAGE4_1R12_BACKEND:-ray}"
STAGE4_1R12_COMMAND="${STAGE4_1R12_COMMAND:-all}"
STAGE4_1R12_RESUME="${STAGE4_1R12_RESUME:-0}"
STAGE4_1R12_OUTPUT_ROOT="${STAGE4_1R12_OUTPUT_ROOT:-${STAGE4_1R12_PROJECT_DIR}/stage4_1r12_runs}"
STAGE4_1R12_TSC_WORKSPACE_ROOT="${STAGE4_1R12_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R12_TSC_RUN_ROOT="${STAGE4_1R12_TSC_RUN_ROOT:-${STAGE4_1R12_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r12_${UID:-0}}"

stage4_1r12_find_source_r11() {
  local explicit="${STAGE4_1R12_SOURCE_STAGE4_1R11_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    [[ -d "${explicit}" ]] || { echo "ERROR: explicit R11 source directory missing: ${explicit}" >&2; return 1; }
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R12_PROJECT_DIR}/stage4_1r11_runs/latest_stage4_1r11_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" \
       && -f "${candidate}/stage4_1r11_state.json" \
       && -f "${candidate}/stage4_1r11_analysis/stage4_1r11_verdict.json" \
       && -f "${candidate}/stage4_1r11_oracle_long_hold/summary.json" \
       && -f "${candidate}/stage4_1r11_calibrated_long_hold/summary.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if [[ -f "${candidate}/stage4_1r11_manifest.json" \
       && -f "${candidate}/stage4_1r11_state.json" \
       && -f "${candidate}/stage4_1r11_analysis/stage4_1r11_verdict.json" \
       && -f "${candidate}/stage4_1r11_oracle_long_hold/summary.json" \
       && -f "${candidate}/stage4_1r11_calibrated_long_hold/summary.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R12_PROJECT_DIR}/stage4_1r11_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r11_frozen_terminal_long_horizon_hold_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r12_new_run_dir() {
  mkdir -p "${STAGE4_1R12_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R12_OUTPUT_ROOT}/stage4_1r12_original_deadline_weak_slew_anticipatory_damping_${stamp}"
}

stage4_1r12_validate_common() {
  [[ -x "${STAGE4_1R12_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R12_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R12_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R12_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R12_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_1R12_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_1R12_BACKEND}" == "ray" || "${STAGE4_1R12_BACKEND}" == "serial" ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R12_RESUME}" == "0" || "${STAGE4_1R12_RESUME}" == "1" ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R12_COMMAND}" in
    all|audit|development|holdout|confirmation|grid) ;;
    *) echo "ERROR: invalid command ${STAGE4_1R12_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_1r12_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R12_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R12_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R12_WORKERS STAGE4_1R12_TSC_WORKSPACE_ROOT STAGE4_1R12_TSC_RUN_ROOT RAY_TMPDIR
  local suffix
  for suffix in R11 R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${suffix}_TSC_WORKSPACE_ROOT=${STAGE4_1R12_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${suffix}_TSC_RUN_ROOT=${STAGE4_1R12_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R12_TSC_RUN_ROOT}"
}
