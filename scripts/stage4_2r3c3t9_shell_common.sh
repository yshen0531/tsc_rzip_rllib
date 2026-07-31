#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T9_PROJECT_DIR="${STAGE4_2R3C3T9_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T9_CONFIG="${STAGE4_2R3C3T9_CONFIG:-${STAGE4_2R3C3T9_PROJECT_DIR}/configs/stage4_2r3c3t9_pc3_mixed_interaction_identification_500ms.json}"
STAGE4_2R3C3T9_PYTHON="${STAGE4_2R3C3T9_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T9_WORKERS="${STAGE4_2R3C3T9_WORKERS:-128}"
STAGE4_2R3C3T9_BACKEND="${STAGE4_2R3C3T9_BACKEND:-ray}"
STAGE4_2R3C3T9_COMMAND="${STAGE4_2R3C3T9_COMMAND:-all}"
STAGE4_2R3C3T9_RESUME="${STAGE4_2R3C3T9_RESUME:-0}"
STAGE4_2R3C3T9_OUTPUT_ROOT="${STAGE4_2R3C3T9_OUTPUT_ROOT:-${STAGE4_2R3C3T9_PROJECT_DIR}/stage4_2r3c3t9_runs}"
STAGE4_2R3C3T9_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T9_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T9_TSC_RUN_ROOT="${STAGE4_2R3C3T9_TSC_RUN_ROOT:-${STAGE4_2R3C3T9_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t9_${UID:-0}}"

STAGE4_2R3C3T2_PROJECT_DIR="${STAGE4_2R3C3T9_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t2_shell_common.sh
source "${STAGE4_2R3C3T9_PROJECT_DIR}/scripts/stage4_2r3c3t2_shell_common.sh"

stage4_2r3c3t9_find_source_r3b() {
  stage4_2r3c3t2_find_source_r3b
}

stage4_2r3c3t9_find_source_r3c3() {
  stage4_2r3c3t2_find_source_r3c3
}

stage4_2r3c3t9_find_source_bank() {
  stage4_2r3c3t2_find_source_bank
}

stage4_2r3c3t9_find_source_t1() {
  stage4_2r3c3t2_find_source_t1
}

stage4_2r3c3t9_find_source_t1_audit() {
  stage4_2r3c3t2_find_source_t1_audit
}

stage4_2r3c3t9_find_t7_controller_bank() {
  local path expected actual
  path="${STAGE4_2R3C3T9_PROJECT_DIR}/stage4_2r3c3t7_basis_feasibility/stage4_2r3c3t7_basis_feasibility_20260731_d530ed5/stage4_2r3c3t7_controller_bank_v1.json"
  expected="fef1eb299cede180c1f43d8713b3174aa9afd8724ea6af4509b06ad5d92febd8"
  [[ -f "${path}" ]] || {
    echo "ERROR: exact T7 controller bank missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: T7 controller bank SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t9_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T9_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3C3T9_OUTPUT_ROOT}/stage4_2r3c3t9_pc3_mixed_interaction_identification_${stamp}"
}

stage4_2r3c3t9_validate_common() {
  [[ -x "${STAGE4_2R3C3T9_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T9_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T9_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3C3T9_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T9_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3c3T9 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T9_BACKEND}" == ray || "${STAGE4_2R3C3T9_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T9_RESUME}" == 0 || "${STAGE4_2R3C3T9_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3C3T9_COMMAND}" in
    all|offline) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3C3T9_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3c3t9_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T9_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T9_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T9_WORKERS
  export STAGE4_2R3C3T9_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T9_TSC_RUN_ROOT
  export RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T9_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T9_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
