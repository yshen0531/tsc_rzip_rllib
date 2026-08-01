#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T12_PROJECT_DIR="${STAGE4_2R3C3T12_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T12_CONFIG="${STAGE4_2R3C3T12_CONFIG:-${STAGE4_2R3C3T12_PROJECT_DIR}/configs/stage4_2r3c3t12_formal_gap_route_discriminator_v1.json}"
STAGE4_2R3C3T12_PYTHON="${STAGE4_2R3C3T12_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T12_OUTPUT_ROOT="${STAGE4_2R3C3T12_OUTPUT_ROOT:-${STAGE4_2R3C3T12_PROJECT_DIR}/stage4_2r3c3t12_route_audits}"

stage4_2r3c3t12_find_t11_run() {
  local path
  path="${STAGE4_2R3C3T12_PROJECT_DIR}/stage4_2r3c3t11_runs/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9"
  [[ -d "${path}" ]] || {
    echo "ERROR: exact immutable T11 run missing: ${path}" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t12_find_t11_audit() {
  local path expected actual
  path="${STAGE4_2R3C3T12_PROJECT_DIR}/stage4_2r3c3t11_audits/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9"
  expected="02933f9ee05f91f6db565e955e0106c65dc6591f273fb562e68ac2767d28c19c"
  [[ -f "${path}/stage4_2r3c3t11_server_audit.json" ]] || {
    echo "ERROR: exact immutable T11 audit missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t11_server_audit.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable T11 server audit SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t12_new_output_dir() {
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T12_OUTPUT_ROOT}/stage4_2r3c3t12_formal_gap_route_discriminator_${stamp}"
}

stage4_2r3c3t12_validate_common() {
  [[ -x "${STAGE4_2R3C3T12_PYTHON}" ]] || {
    echo "ERROR: Python not executable: ${STAGE4_2R3C3T12_PYTHON}" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T12_CONFIG}" ]] || {
    echo "ERROR: T12 config missing: ${STAGE4_2R3C3T12_CONFIG}" >&2
    return 1
  }
}

stage4_2r3c3t12_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T12_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T12_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
