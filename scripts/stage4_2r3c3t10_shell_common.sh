#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T10_PROJECT_DIR="${STAGE4_2R3C3T10_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T10_CONFIG="${STAGE4_2R3C3T10_CONFIG:-${STAGE4_2R3C3T10_PROJECT_DIR}/configs/stage4_2r3c3t10_interaction_aware_feasibility_v1.json}"
STAGE4_2R3C3T10_T9_CONFIG="${STAGE4_2R3C3T10_T9_CONFIG:-${STAGE4_2R3C3T10_PROJECT_DIR}/configs/stage4_2r3c3t9_pc3_mixed_interaction_identification_500ms.json}"
STAGE4_2R3C3T10_PYTHON="${STAGE4_2R3C3T10_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T10_OUTPUT_ROOT="${STAGE4_2R3C3T10_OUTPUT_ROOT:-${STAGE4_2R3C3T10_PROJECT_DIR}/stage4_2r3c3t10_interaction_feasibility}"

STAGE4_2R3C3T9_PROJECT_DIR="${STAGE4_2R3C3T10_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t9_shell_common.sh
source "${STAGE4_2R3C3T10_PROJECT_DIR}/scripts/stage4_2r3c3t9_shell_common.sh"

stage4_2r3c3t10_find_t9_run() {
  local path
  path="${STAGE4_2R3C3T10_PROJECT_DIR}/stage4_2r3c3t9_runs/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005"
  [[ -d "${path}" ]] || {
    echo "ERROR: exact immutable T9 run missing: ${path}" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t10_find_t9_audit() {
  local path expected actual
  path="${STAGE4_2R3C3T10_PROJECT_DIR}/stage4_2r3c3t9_audits/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005"
  expected="05547765ca5e1282e58b0d33e454b0a2a4dd87ee16e85146261650510ebd05f8"
  [[ -f "${path}/stage4_2r3c3t9_server_audit.json" ]] || {
    echo "ERROR: exact immutable T9 audit missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t9_server_audit.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable T9 server audit SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t10_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T10_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T10_OUTPUT_ROOT}/stage4_2r3c3t10_interaction_aware_feasibility_${stamp}"
}

stage4_2r3c3t10_validate_common() {
  [[ -x "${STAGE4_2R3C3T10_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T10_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T10_CONFIG}" ]] || {
    echo "ERROR: T10 config missing: ${STAGE4_2R3C3T10_CONFIG}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T10_T9_CONFIG}" ]] || {
    echo "ERROR: T9 config missing: ${STAGE4_2R3C3T10_T9_CONFIG}" >&2
    return 1
  }
}

stage4_2r3c3t10_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T10_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T10_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
