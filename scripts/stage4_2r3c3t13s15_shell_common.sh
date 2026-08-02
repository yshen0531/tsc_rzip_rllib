#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S15_PROJECT_DIR="${STAGE4_2R3C3T13S15_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S15_CONFIG="${STAGE4_2R3C3T13S15_CONFIG:-${STAGE4_2R3C3T13S15_PROJECT_DIR}/configs/stage4_2r3c3t13s15_fixed_basis_local_identification_370ms.json}"
STAGE4_2R3C3T13S15_PYTHON="${STAGE4_2R3C3T13S15_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S15_WORKERS="${STAGE4_2R3C3T13S15_WORKERS:-128}"
STAGE4_2R3C3T13S15_BACKEND="${STAGE4_2R3C3T13S15_BACKEND:-ray}"
STAGE4_2R3C3T13S15_COMMAND="${STAGE4_2R3C3T13S15_COMMAND:-offline}"
STAGE4_2R3C3T13S15_RESUME="${STAGE4_2R3C3T13S15_RESUME:-0}"
STAGE4_2R3C3T13S15_OUTPUT_ROOT="${STAGE4_2R3C3T13S15_OUTPUT_ROOT:-${STAGE4_2R3C3T13S15_PROJECT_DIR}/stage4_2r3c3t13s15_runs}"
STAGE4_2R3C3T13S15_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S15_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S15_TSC_RUN_ROOT="${STAGE4_2R3C3T13S15_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S15_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s15_${UID:-0}}"

STAGE4_2R3C3T13S13_PROJECT_DIR="${STAGE4_2R3C3T13S15_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s13_shell_common.sh
source "${STAGE4_2R3C3T13S15_PROJECT_DIR}/scripts/stage4_2r3c3t13s13_shell_common.sh"

stage4_2r3c3t13s15_find_source_r3b() { stage4_2r3c3t13s13_find_source_r3b; }
stage4_2r3c3t13s15_find_source_r3c3() { stage4_2r3c3t13s13_find_source_r3c3; }
stage4_2r3c3t13s15_find_source_bank() { stage4_2r3c3t13s13_find_source_bank; }
stage4_2r3c3t13s15_find_source_t1() { stage4_2r3c3t13s13_find_source_t1; }
stage4_2r3c3t13s15_find_source_t1_audit() { stage4_2r3c3t13s13_find_source_t1_audit; }
stage4_2r3c3t13s15_find_t3_controller_bank() { stage4_2r3c3t13s13_find_t3_controller_bank; }
stage4_2r3c3t13s15_q1_run() { stage4_2r3c3t13s13_q1_run; }
stage4_2r3c3t13s15_q2_run() { stage4_2r3c3t13s13_q2_run; }
stage4_2r3c3t13s15_q1_audit() { stage4_2r3c3t13s13_q1_audit; }
stage4_2r3c3t13s15_q2_audit() { stage4_2r3c3t13s13_q2_audit; }
stage4_2r3c3t13s15_r3b_audit() { stage4_2r3c3t13s13_r3b_audit; }
stage4_2r3c3t13s15_r3b_snapshot_checks() { stage4_2r3c3t13s13_r3b_snapshot_checks; }

stage4_2r3c3t13s15_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S15_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S15_OUTPUT_ROOT}/stage4_2r3c3t13s15_fixed_basis_local_identification_${stamp}"
}

stage4_2r3c3t13s15_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S15_PYTHON}" ]] || { echo "ERROR: Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S15_CONFIG}" ]] || { echo "ERROR: config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S15_WORKERS}" == 128 ]] || { echo "ERROR: T13S15 capacity is frozen at 128" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S15_BACKEND}" == ray || "${STAGE4_2R3C3T13S15_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S15_RESUME}" == 0 || "${STAGE4_2R3C3T13S15_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S15_COMMAND}" in
    offline|baseline|probe|finalize|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s15_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S15_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S15_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T13S15_WORKERS STAGE4_2R3C3T13S15_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T13S15_TSC_RUN_ROOT RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S15_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T13S15_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
