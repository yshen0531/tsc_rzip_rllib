#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R9_PROJECT_DIR="${STAGE4_1R9_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R9_CONFIG="${STAGE4_1R9_CONFIG:-${STAGE4_1R9_PROJECT_DIR}/configs/stage4_1r9_terminal_template_mpc_feedback_hold_550ms.json}"
STAGE4_1R9_PYTHON="${STAGE4_1R9_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R9_WORKERS="${STAGE4_1R9_WORKERS:-128}"
STAGE4_1R9_BACKEND="${STAGE4_1R9_BACKEND:-ray}"
STAGE4_1R9_COMMAND="${STAGE4_1R9_COMMAND:-all}"
STAGE4_1R9_RESUME="${STAGE4_1R9_RESUME:-0}"
STAGE4_1R9_OUTPUT_ROOT="${STAGE4_1R9_OUTPUT_ROOT:-${STAGE4_1R9_PROJECT_DIR}/stage4_1r9_runs}"
STAGE4_1R9_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R9_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT:-${STAGE4_1R9_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r9_${UID:-0}}"

stage4_1r9_find_source_r8() {
  local explicit="${STAGE4_1R9_SOURCE_STAGE4_1R8_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R9_PROJECT_DIR}/stage4_1r8_runs/latest_stage4_1r8_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" && -f "${candidate}/stage4_1r8_state.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if [[ -f "${candidate}/stage4_1r8_manifest.json" \
       && -f "${candidate}/stage4_1r8_state.json" \
       && -f "${candidate}/stage4_1r8_analysis/stage4_1r8_verdict.json" \
       && -f "${candidate}/stage4_1r8_integrated_calibration/summary.json" \
       && -f "${candidate}/stage4_1r8_oracle_queue_tail/summary.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R9_PROJECT_DIR}/stage4_1r8_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r8_trusted_batch_calibration_queue_tail_closure_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r9_new_run_dir() {
  mkdir -p "${STAGE4_1R9_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R9_OUTPUT_ROOT}/stage4_1r9_terminal_template_mpc_feedback_hold_${stamp}"
}

stage4_1r9_validate_common() {
  [[ -x "${STAGE4_1R9_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R9_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R9_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R9_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R9_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_1R9_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_1R9_BACKEND}" == "ray" || "${STAGE4_1R9_BACKEND}" == "serial" ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R9_RESUME}" == "0" || "${STAGE4_1R9_RESUME}" == "1" ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R9_COMMAND}" in
    all|prepare|audit|oracle|startup|analyze) ;;
    *) echo "ERROR: invalid command ${STAGE4_1R9_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_1r9_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R9_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R9_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R9_WORKERS STAGE4_1R9_TSC_WORKSPACE_ROOT STAGE4_1R9_TSC_RUN_ROOT RAY_TMPDIR
  # Nested frozen contexts are data/code dependencies only.  They all use the
  # same bounded scratch root and may not silently create independent campaigns.
  export STAGE4_1R8_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R8_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT}"
  export STAGE4_1R7_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R7_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT}"
  export STAGE4_1R6_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R6_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT}"
  export STAGE4_1R5_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R5_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT}"
  export STAGE4_1R4_TSC_WORKSPACE_ROOT="${STAGE4_1R9_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R4_TSC_RUN_ROOT="${STAGE4_1R9_TSC_RUN_ROOT}"
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R9_TSC_RUN_ROOT}"
}
