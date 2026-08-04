#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14_CONFIG="${STAGE4_2R3C3T13S24D1R14_CONFIG:-${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R14_PYTHON="${STAGE4_2R3C3T13S24D1R14_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14_WORKERS="${STAGE4_2R3C3T13S24D1R14_WORKERS:-72}"
STAGE4_2R3C3T13S24D1R14_BACKEND="${STAGE4_2R3C3T13S24D1R14_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R14_COMMAND="${STAGE4_2R3C3T13S24D1R14_COMMAND:-offline}"
STAGE4_2R3C3T13S24D1R14_RESUME="${STAGE4_2R3C3T13S24D1R14_RESUME:-0}"
STAGE4_2R3C3T13S24D1R14_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}/stage4_2r3c3t13s24d1r14_runs}"
STAGE4_2R3C3T13S24D1R14_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R14_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R14_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r14_${UID:-0}}"

STAGE4_2R3C3T13S24D1R13_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R13_PYTHON="${STAGE4_2R3C3T13S24D1R14_PYTHON}"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r13_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r13_shell_common.sh"

stage4_2r3c3t13s24d1r14_find_source_d1r13() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}/stage4_2r3c3t13s24d1r13_runs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_20260804_df3910f_v1"
  [[ -f "${path}/final_result.json" ]] || { echo "ERROR: exact immutable D1R13 final result missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel/stage_state.json" ]] || { echo "ERROR: exact immutable D1R13 state missing" >&2; return 1; }
  [[ -d "${path}/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel/raw" ]] || { echo "ERROR: exact immutable D1R13 raw missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14_find_source_d1r13_audit() {
  local run
  run="$(stage4_2r3c3t13s24d1r14_find_source_d1r13)"
  [[ -f "${run}/server_independent_forensics_v1.json" ]] || { echo "ERROR: exact D1R13 independent audit missing" >&2; return 1; }
  printf '%s\n' "${run}/server_independent_forensics_v1.json"
}

stage4_2r3c3t13s24d1r14_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R14_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r14_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R14_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R14_CONFIG}" ]] || { echo "ERROR: D1R14 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14_WORKERS}" == 72 ]] || { echo "ERROR: D1R14 capacity is frozen at 72" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R14_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R14_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R14_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R14_COMMAND}" in
    offline|run|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r14_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24D1R13_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24D1R13_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24d1r13_export_runtime
}
