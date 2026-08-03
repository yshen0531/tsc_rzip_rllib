#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S23_PROJECT_DIR="${STAGE4_2R3C3T13S23_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S23_CONFIG="${STAGE4_2R3C3T13S23_CONFIG:-${STAGE4_2R3C3T13S23_PROJECT_DIR}/configs/stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_v1.json}"
STAGE4_2R3C3T13S23_S21_CONFIG="${STAGE4_2R3C3T13S23_S21_CONFIG:-${STAGE4_2R3C3T13S23_PROJECT_DIR}/configs/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_370ms.json}"
STAGE4_2R3C3T13S23_PYTHON="${STAGE4_2R3C3T13S23_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S23_OUTPUT_ROOT="${STAGE4_2R3C3T13S23_OUTPUT_ROOT:-${STAGE4_2R3C3T13S23_PROJECT_DIR}/stage4_2r3c3t13s23_audits}"

STAGE4_2R3C3T13S21_PROJECT_DIR="${STAGE4_2R3C3T13S23_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s21_shell_common.sh
source "${STAGE4_2R3C3T13S23_PROJECT_DIR}/scripts/stage4_2r3c3t13s21_shell_common.sh"

stage4_2r3c3t13s23_find_s21_run() {
  local path expected actual
  path="${STAGE4_2R3C3T13S23_PROJECT_DIR}/stage4_2r3c3t13s21_runs/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353"
  expected="01ebdfab81d8d24f96d222846a71ee23c49daafbe93c7fabe2c49cb0a2e60fd1"
  [[ -f "${path}/stage4_2r3c3t13s21_state.json" ]] || {
    echo "ERROR: exact immutable S21 run missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s21_state.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable S21 final state SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s23_find_s22_output() {
  local path expected actual
  path="${STAGE4_2R3C3T13S23_PROJECT_DIR}/stage4_2r3c3t13s22_audits/stage4_2r3c3t13s22_full_horizon_affine_authority_20260803_080437"
  expected="3559187879dc5630f2688d0adb64b83391fc286eca14f6a531fae1c90fa4f01e"
  [[ -f "${path}/stage4_2r3c3t13s22_summary_v1.json" ]] || {
    echo "ERROR: exact immutable S22 output missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s22_summary_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable S22 summary SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s23_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T13S23_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S23_OUTPUT_ROOT}/stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_${stamp}"
}

stage4_2r3c3t13s23_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S23_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23_CONFIG}" ]] || {
    echo "ERROR: S23 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23_S21_CONFIG}" ]] || {
    echo "ERROR: S21 source config missing" >&2
    return 1
  }
}

stage4_2r3c3t13s23_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S23_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S23_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
