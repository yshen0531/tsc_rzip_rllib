#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14R6_CONFIG="${STAGE4_2R3C3T13S24D1R14R6_CONFIG:-${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R14R6_PYTHON="${STAGE4_2R3C3T13S24D1R14R6_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14R6_WORKERS="${STAGE4_2R3C3T13S24D1R14R6_WORKERS:-96}"
STAGE4_2R3C3T13S24D1R14R6_BACKEND="${STAGE4_2R3C3T13S24D1R14R6_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R14R6_COMMAND="${STAGE4_2R3C3T13S24D1R14R6_COMMAND:-offline}"
STAGE4_2R3C3T13S24D1R14R6_RESUME="${STAGE4_2R3C3T13S24D1R14R6_RESUME:-0}"
STAGE4_2R3C3T13S24D1R14R6_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R6_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r6_runs}"
STAGE4_2R3C3T13S24D1R14R6_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14R6_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R14R6_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14R6_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R14R6_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r14r6_${UID:-0}}"

STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R14R4_PYTHON="${STAGE4_2R3C3T13S24D1R14R6_PYTHON}"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r4_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r4_shell_common.sh"

stage4_2r3c3t13s24d1r14r6_find_source_r4() {
  local path="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r4_runs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1"
  [[ -f "${path}/final_result.json" ]] || { echo "ERROR: exact R4 final result missing" >&2; return 1; }
  [[ -f "${path}/server_independent_forensics_v1.json" ]] || { echo "ERROR: exact R4 independent result missing" >&2; return 1; }
  [[ -d "${path}/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel/raw" ]] || { echo "ERROR: exact R4 raw missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r6_find_source_r5() {
  local path="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r5_audits/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_20260804_bb829f3_v3"
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r5_summary_v1.json" ]] || { echo "ERROR: exact R5 summary missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r5_independent_v1.json" ]] || { echo "ERROR: exact R5 independent result missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r6_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14R6_OUTPUT_ROOT}"
  local stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R14R6_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r14r6_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R14R6_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R6_CONFIG}" ]] || { echo "ERROR: R6 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14R6_WORKERS}" == 96 ]] || { echo "ERROR: R6 capacity is frozen at 96" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14R6_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R14R6_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R14R6_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R14R6_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R14R6_COMMAND}" in offline|run|postprocess) ;; *) return 1 ;; esac
}

stage4_2r3c3t13s24d1r14r6_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14R6_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24D1R14R4_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14R6_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24D1R14R4_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14R6_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24d1r14r4_export_runtime
}
