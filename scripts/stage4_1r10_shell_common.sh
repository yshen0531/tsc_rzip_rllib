#!/usr/bin/env bash
set -euo pipefail

STAGE4_1R10_PROJECT_DIR="${STAGE4_1R10_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_1R10_CONFIG="${STAGE4_1R10_CONFIG:-${STAGE4_1R10_PROJECT_DIR}/configs/stage4_1r10_queue_preview_terminal_transition_hold_750ms.json}"
STAGE4_1R10_PYTHON="${STAGE4_1R10_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_1R10_WORKERS="${STAGE4_1R10_WORKERS:-128}"
STAGE4_1R10_BACKEND="${STAGE4_1R10_BACKEND:-ray}"
STAGE4_1R10_COMMAND="${STAGE4_1R10_COMMAND:-all}"
STAGE4_1R10_RESUME="${STAGE4_1R10_RESUME:-0}"
STAGE4_1R10_OUTPUT_ROOT="${STAGE4_1R10_OUTPUT_ROOT:-${STAGE4_1R10_PROJECT_DIR}/stage4_1r10_runs}"
STAGE4_1R10_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_1R10_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT:-${STAGE4_1R10_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r10_${UID:-0}}"

stage4_1r10_find_source_r9() {
  local explicit="${STAGE4_1R10_SOURCE_STAGE4_1R9_RUN:-}"
  if [[ -n "${explicit}" ]]; then
    printf '%s\n' "${explicit}"
    return 0
  fi
  local latest_file="${STAGE4_1R10_PROJECT_DIR}/stage4_1r9_runs/latest_stage4_1r9_run.txt"
  if [[ -f "${latest_file}" ]]; then
    local candidate
    candidate="$(tr -d '\r\n' < "${latest_file}")"
    if [[ -d "${candidate}" && -f "${candidate}/stage4_1r9_state.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi
  local candidate
  while IFS= read -r candidate; do
    if [[ -f "${candidate}/stage4_1r9_manifest.json" \
       && -f "${candidate}/stage4_1r9_state.json" \
       && -f "${candidate}/stage4_1r9_analysis/stage4_1r9_verdict.json" \
       && -f "${candidate}/stage4_1r9_oracle_development/summary.json" \
       && -f "${candidate}/stage4_1r9_oracle_development/results.json" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(find "${STAGE4_1R10_PROJECT_DIR}/stage4_1r9_runs" -mindepth 1 -maxdepth 1 -type d -name 'stage4_1r9_terminal_template_mpc_feedback_hold_*' -print 2>/dev/null | sort -r)
  return 1
}

stage4_1r10_new_run_dir() {
  mkdir -p "${STAGE4_1R10_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_1R10_OUTPUT_ROOT}/stage4_1r10_queue_preview_terminal_transition_hold_${stamp}"
}

stage4_1r10_validate_common() {
  [[ -x "${STAGE4_1R10_PYTHON}" ]] || { echo "ERROR: Python not executable: ${STAGE4_1R10_PYTHON}" >&2; return 1; }
  [[ -f "${STAGE4_1R10_CONFIG}" ]] || { echo "ERROR: config missing: ${STAGE4_1R10_CONFIG}" >&2; return 1; }
  [[ "${STAGE4_1R10_WORKERS}" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: STAGE4_1R10_WORKERS must be positive" >&2; return 1; }
  [[ "${STAGE4_1R10_BACKEND}" == "ray" || "${STAGE4_1R10_BACKEND}" == "serial" ]] || { echo "ERROR: backend must be ray or serial" >&2; return 1; }
  [[ "${STAGE4_1R10_RESUME}" == "0" || "${STAGE4_1R10_RESUME}" == "1" ]] || { echo "ERROR: resume must be 0 or 1" >&2; return 1; }
  case "${STAGE4_1R10_COMMAND}" in
    all|prepare|audit|oracle|startup|analyze) ;;
    *) echo "ERROR: invalid command ${STAGE4_1R10_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_1r10_export_runtime() {
  export PROJECT_DIR="${STAGE4_1R10_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_1R10_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_1R10_WORKERS STAGE4_1R10_TSC_WORKSPACE_ROOT STAGE4_1R10_TSC_RUN_ROOT RAY_TMPDIR
  # Nested frozen contexts are source-code/data dependencies only. They share
  # one bounded scratch root and may not create independent campaigns.
  export STAGE4_1R9_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R9_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  export STAGE4_1R8_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R8_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  export STAGE4_1R7_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R7_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  export STAGE4_1R6_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R6_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  export STAGE4_1R5_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R5_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  export STAGE4_1R4_TSC_WORKSPACE_ROOT="${STAGE4_1R10_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R4_TSC_RUN_ROOT="${STAGE4_1R10_TSC_RUN_ROOT}"
  mkdir -p "${RAY_TMPDIR}" "${STAGE4_1R10_TSC_RUN_ROOT}"
}
