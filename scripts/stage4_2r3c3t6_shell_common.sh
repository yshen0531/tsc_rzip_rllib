#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T6_PROJECT_DIR="${STAGE4_2R3C3T6_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T6_CONFIG="${STAGE4_2R3C3T6_CONFIG:-${STAGE4_2R3C3T6_PROJECT_DIR}/configs/stage4_2r3c3t6_target_residual_new_direction_identification_500ms.json}"
STAGE4_2R3C3T6_PYTHON="${STAGE4_2R3C3T6_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T6_WORKERS="${STAGE4_2R3C3T6_WORKERS:-128}"
STAGE4_2R3C3T6_BACKEND="${STAGE4_2R3C3T6_BACKEND:-ray}"
STAGE4_2R3C3T6_COMMAND="${STAGE4_2R3C3T6_COMMAND:-all}"
STAGE4_2R3C3T6_RESUME="${STAGE4_2R3C3T6_RESUME:-0}"
STAGE4_2R3C3T6_OUTPUT_ROOT="${STAGE4_2R3C3T6_OUTPUT_ROOT:-${STAGE4_2R3C3T6_PROJECT_DIR}/stage4_2r3c3t6_runs}"
STAGE4_2R3C3T6_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T6_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T6_TSC_RUN_ROOT="${STAGE4_2R3C3T6_TSC_RUN_ROOT:-${STAGE4_2R3C3T6_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t6_${UID:-0}}"

STAGE4_2R3C3T2_PROJECT_DIR="${STAGE4_2R3C3T6_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t2_shell_common.sh
source "${STAGE4_2R3C3T6_PROJECT_DIR}/scripts/stage4_2r3c3t2_shell_common.sh"

stage4_2r3c3t6_find_source_r3b() {
  stage4_2r3c3t2_find_source_r3b
}

stage4_2r3c3t6_find_source_r3c3() {
  stage4_2r3c3t2_find_source_r3c3
}

stage4_2r3c3t6_find_source_bank() {
  stage4_2r3c3t2_find_source_bank
}

stage4_2r3c3t6_find_source_t1() {
  stage4_2r3c3t2_find_source_t1
}

stage4_2r3c3t6_find_source_t1_audit() {
  stage4_2r3c3t2_find_source_t1_audit
}

stage4_2r3c3t6_find_t3_controller_bank() {
  local path expected actual
  path="${STAGE4_2R3C3T6_PROJECT_DIR}/stage4_2r3c3t3_eight_basis_feasibility/stage4_2r3c3t3_eight_basis_feasibility_20260731_1a75fff/stage4_2r3c3t3_eight_basis_controller_bank_v1.json"
  expected="6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86"
  [[ -f "${path}" ]] || {
    echo "ERROR: exact T3 controller bank missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: T3 controller bank SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t6_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T6_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' \
    "${STAGE4_2R3C3T6_OUTPUT_ROOT}/stage4_2r3c3t6_target_residual_new_direction_identification_${stamp}"
}

stage4_2r3c3t6_validate_common() {
  [[ -x "${STAGE4_2R3C3T6_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T6_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T6_CONFIG}" ]] || {
    echo "ERROR: config missing: ${STAGE4_2R3C3T6_CONFIG}" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T6_WORKERS}" == "128" ]] || {
    echo "ERROR: Stage4.2R3c3T6 Ray capacity is frozen at 128 workers" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T6_BACKEND}" == ray || "${STAGE4_2R3C3T6_BACKEND}" == serial ]] || {
    echo "ERROR: backend must be ray or serial" >&2
    return 1
  }
  [[ "${STAGE4_2R3C3T6_RESUME}" == 0 || "${STAGE4_2R3C3T6_RESUME}" == 1 ]] || {
    echo "ERROR: resume must be 0 or 1" >&2
    return 1
  }
  case "${STAGE4_2R3C3T6_COMMAND}" in
    all|offline) ;;
    *) echo "ERROR: invalid command ${STAGE4_2R3C3T6_COMMAND}" >&2; return 1 ;;
  esac
}

stage4_2r3c3t6_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T6_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T6_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T6_WORKERS
  export STAGE4_2R3C3T6_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T6_TSC_RUN_ROOT
  export RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T6_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T6_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
