#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S23D1_PROJECT_DIR="${STAGE4_2R3C3T13S23D1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S23D1_CONFIG="${STAGE4_2R3C3T13S23D1_CONFIG:-${STAGE4_2R3C3T13S23D1_PROJECT_DIR}/configs/stage4_2r3c3t13s23d1_bounded_schedule_redesign_search_v1.json}"
STAGE4_2R3C3T13S23D1_DESIGN="${STAGE4_2R3C3T13S23D1_DESIGN:-${STAGE4_2R3C3T13S23D1_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S23D1_SCHEDULE_REDESIGN_SEARCH.md}"
STAGE4_2R3C3T13S23D1_PYTHON="${STAGE4_2R3C3T13S23D1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S23D1_OUTPUT_ROOT="${STAGE4_2R3C3T13S23D1_OUTPUT_ROOT:-${STAGE4_2R3C3T13S23D1_PROJECT_DIR}/stage4_2r3c3t13s23d1_audits}"

STAGE4_2R3C3T13S23_PROJECT_DIR="${STAGE4_2R3C3T13S23D1_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s23_shell_common.sh
source "${STAGE4_2R3C3T13S23D1_PROJECT_DIR}/scripts/stage4_2r3c3t13s23_shell_common.sh"

stage4_2r3c3t13s23d1_find_s23_output() {
  local path expected actual
  path="${STAGE4_2R3C3T13S23D1_PROJECT_DIR}/stage4_2r3c3t13s23_audits/stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight_20260803_091116"
  expected="5188d583baf977e145eb5d33680b87d4ff901155bd8dd5ba3c662503dfeb50ab"
  [[ -f "${path}/stage4_2r3c3t13s23_summary_v1.json" ]] || {
    echo "ERROR: exact immutable S23 output missing: ${path}" >&2
    return 1
  }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s23_summary_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || {
    echo "ERROR: immutable S23 summary SHA-256 mismatch" >&2
    return 1
  }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s23d1_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T13S23D1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S23D1_OUTPUT_ROOT}/stage4_2r3c3t13s23d1_bounded_schedule_search_${stamp}"
}

stage4_2r3c3t13s23d1_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S23D1_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23D1_CONFIG}" ]] || {
    echo "ERROR: S23D1 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S23D1_DESIGN}" ]] || {
    echo "ERROR: S23D1 design document missing" >&2
    return 1
  }
  stage4_2r3c3t13s23_validate_common
}

stage4_2r3c3t13s23d1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S23D1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S23D1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
