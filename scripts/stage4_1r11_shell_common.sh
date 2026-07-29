#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R11_PROJECT_DIR="${STAGE4_1R11_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R11_CONFIG="${STAGE4_1R11_CONFIG:-${STAGE4_1R11_PROJECT_DIR}/configs/stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json}"
STAGE4_1R11_PYTHON="${STAGE4_1R11_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R11_WORKERS="${STAGE4_1R11_WORKERS:-128}"
STAGE4_1R11_BACKEND="${STAGE4_1R11_BACKEND:-ray}"
STAGE4_1R11_COMMAND="${STAGE4_1R11_COMMAND:-all}"
STAGE4_1R11_RESUME="${STAGE4_1R11_RESUME:-0}"
STAGE4_1R11_OUTPUT_ROOT="${STAGE4_1R11_OUTPUT_ROOT:-${STAGE4_1R11_PROJECT_DIR}/stage4_1r11_runs}"
STAGE4_1R11_TSC_WORKSPACE_ROOT="${STAGE4_1R11_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R11_TSC_RUN_ROOT="${STAGE4_1R11_TSC_RUN_ROOT:-${STAGE4_1R11_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r11_${UID:-0}}"

stage4_1r11_find_source_r10() {
  local explicit="${STAGE4_1R11_SOURCE_STAGE4_1R10_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R11_PROJECT_DIR}/stage4_1r10_runs/latest_stage4_1r10_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" \
       && -f "${candidate}/stage4_1r10_state.json" \
       && -f "${candidate}/stage4_1r10_analysis/stage4_1r10_verdict.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if [[ -f "${candidate}/stage4_1r10_manifest.json" \
       && -f "${candidate}/stage4_1r10_state.json" \
       && -f "${candidate}/stage4_1r10_analysis/stage4_1r10_verdict.json" \
       && -f "${candidate}/stage4_1r10_oracle_development/summary.json" \
       && -f "${candidate}/stage4_1r10_oracle_holdout/summary.json" \
       && -f "${candidate}/stage4_1r10_calibrated_confirmation/summary.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R11_PROJECT_DIR}/stage4_1r10_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r10_queue_preview_terminal_transition_hold_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r11_new_run_dir() {
  mkdir -p "${STAGE4_1R11_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R11_OUTPUT_ROOT}/stage4_1r11_frozen_terminal_long_horizon_hold_${stamp}"
}

stage4_1r11_validate_common() {
  [[ -x "${STAGE4_1R11_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R11_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R11_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R11_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R11_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_1R11_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_1R11_BACKEND}" == "ray" || "${STAGE4_1R11_BACKEND}" == "serial" ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R11_RESUME}" == "0" || "${STAGE4_1R11_RESUME}" == "1" ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R11_COMMAND}" in
    all|prepare|audit|oracle|calibrated|restart|analyze) ;;
    *) echo "ERROR: invalid command ${STAGE4_1R11_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_1r11_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R11_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R11_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R11_WORKERS STAGE4_1R11_TSC_WORKSPACE_ROOT STAGE4_1R11_TSC_RUN_ROOT RAY_TMPDIR
  # All nested stages are frozen code/data dependencies and share one bounded
  # scratch tree; they do not spawn independent campaigns.
  local stage
  for stage in R10 R9 R8 R7 R6 R5 R4; do
    export "STAGE4_1${stage}_TSC_WORKSPACE_ROOT=${STAGE4_1R11_TSC_WORKSPACE_ROOT}"
    export "STAGE4_1${stage}_TSC_RUN_ROOT=${STAGE4_1R11_TSC_RUN_ROOT}"
  done
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R11_TSC_RUN_ROOT}"
}
