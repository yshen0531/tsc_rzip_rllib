#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S5_PROJECT_DIR="${STAGE4_2R3C3T13S5_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S5_CONFIG="${STAGE4_2R3C3T13S5_CONFIG:-${STAGE4_2R3C3T13S5_PROJECT_DIR}/configs/stage4_2r3c3t13s5_lattice_native_split_holdout_370ms.json}"
STAGE4_2R3C3T13S5_PYTHON="${STAGE4_2R3C3T13S5_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S5_WORKERS="${STAGE4_2R3C3T13S5_WORKERS:-68}"
STAGE4_2R3C3T13S5_BACKEND="${STAGE4_2R3C3T13S5_BACKEND:-ray}"
STAGE4_2R3C3T13S5_COMMAND="${STAGE4_2R3C3T13S5_COMMAND:-all}"
STAGE4_2R3C3T13S5_RESUME="${STAGE4_2R3C3T13S5_RESUME:-0}"
STAGE4_2R3C3T13S5_OUTPUT_ROOT="${STAGE4_2R3C3T13S5_OUTPUT_ROOT:-${STAGE4_2R3C3T13S5_PROJECT_DIR}/stage4_2r3c3t13s5_runs}"
STAGE4_2R3C3T13S5_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S5_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S5_TSC_RUN_ROOT="${STAGE4_2R3C3T13S5_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S5_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s5_${UID:-0}}"

STAGE4_2R3C3T11_PROJECT_DIR="${STAGE4_2R3C3T13S5_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t11_shell_common.sh
source "${STAGE4_2R3C3T13S5_PROJECT_DIR}/scripts/stage4_2r3c3t11_shell_common.sh"

stage4_2r3c3t13s5_find_source_r3b() { stage4_2r3c3t11_find_source_r3b; }
stage4_2r3c3t13s5_find_source_r3c3() { stage4_2r3c3t11_find_source_r3c3; }
stage4_2r3c3t13s5_find_source_bank() { stage4_2r3c3t11_find_source_bank; }
stage4_2r3c3t13s5_find_source_t1() { stage4_2r3c3t11_find_source_t1; }
stage4_2r3c3t13s5_find_source_t1_audit() { stage4_2r3c3t11_find_source_t1_audit; }
stage4_2r3c3t13s5_find_t3_controller_bank() { stage4_2r3c3t11_find_t3_controller_bank; }

stage4_2r3c3t13s5_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S5_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S5_OUTPUT_ROOT}/stage4_2r3c3t13s5_lattice_native_split_holdout_${stamp}"
}

stage4_2r3c3t13s5_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S5_PYTHON}" ]] || { echo "ERROR: Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S5_CONFIG}" ]] || { echo "ERROR: config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S5_WORKERS}" == "68" ]] || { echo "ERROR: T13S5 capacity is frozen at 68" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S5_BACKEND}" == ray || "${STAGE4_2R3C3T13S5_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S5_RESUME}" == 0 || "${STAGE4_2R3C3T13S5_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S5_COMMAND}" in all|offline) ;; *) return 1 ;; esac
}

stage4_2r3c3t13s5_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S5_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S5_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T13S5_WORKERS STAGE4_2R3C3T13S5_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T13S5_TSC_RUN_ROOT RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S5_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T13S5_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
