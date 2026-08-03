#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S23R1_PROJECT_DIR="${STAGE4_2R3C3T13S23R1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S23R1_CONFIG="${STAGE4_2R3C3T13S23R1_CONFIG:-${STAGE4_2R3C3T13S23R1_PROJECT_DIR}/configs/stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight_v1.json}"
STAGE4_2R3C3T13S23R1_DESIGN="${STAGE4_2R3C3T13S23R1_DESIGN:-${STAGE4_2R3C3T13S23R1_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S23R1_AMPLITUDE_CODED_HADAMARD_PREFLIGHT_DESIGN.md}"
STAGE4_2R3C3T13S23R1_PYTHON="${STAGE4_2R3C3T13S23R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S23R1_OUTPUT_ROOT="${STAGE4_2R3C3T13S23R1_OUTPUT_ROOT:-${STAGE4_2R3C3T13S23R1_PROJECT_DIR}/stage4_2r3c3t13s23r1_audits}"

STAGE4_2R3C3T13S23D1_PROJECT_DIR="${STAGE4_2R3C3T13S23R1_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s23d1_shell_common.sh
source "${STAGE4_2R3C3T13S23R1_PROJECT_DIR}/scripts/stage4_2r3c3t13s23d1_shell_common.sh"

stage4_2r3c3t13s23r1_find_d1_output() {
  local path expected actual
  path="${STAGE4_2R3C3T13S23R1_PROJECT_DIR}/stage4_2r3c3t13s23d1_audits/stage4_2r3c3t13s23d1_bounded_schedule_search_20260803_095124"
  expected="c00d651454767781d88cf5d83ee861dd2a666b7fd069d47db3c6b24e211a9c0a"
  [[ -f "${path}/stage4_2r3c3t13s23d1_summary_v1.json" ]] || {
    echo "ERROR: exact immutable S23D1 output missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s23d1_summary_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable S23D1 summary SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s23r1_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T13S23R1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S23R1_OUTPUT_ROOT}/stage4_2r3c3t13s23r1_amplitude_coded_preflight_${stamp}"
}

stage4_2r3c3t13s23r1_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S23R1_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23R1_CONFIG}" ]] || {
    echo "ERROR: S23R1 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23R1_DESIGN}" ]] || {
    echo "ERROR: S23R1 design missing" >&2
    return 1
  }
  stage4_2r3c3t13s23d1_validate_common
}

stage4_2r3c3t13s23r1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S23R1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S23R1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
