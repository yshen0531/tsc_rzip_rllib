#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R1_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R1_CONFIG="${STAGE4_2R3C3T13S24D1R1_CONFIG:-${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1.json}"
STAGE4_2R3C3T13S24D1R1_DESIGN="${STAGE4_2R3C3T13S24D1R1_DESIGN:-${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S24D1R1_GEOMETRY_RESTORING_AMPLITUDE_SEARCH_DESIGN.md}"
STAGE4_2R3C3T13S24D1R1_PYTHON="${STAGE4_2R3C3T13S24D1R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R1_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R1_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}/stage4_2r3c3t13s24d1r1_audits}"

STAGE4_2R3C3T13S24D1_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s24d1_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1_shell_common.sh"

stage4_2r3c3t13s24d1r1_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R1_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R1_CONFIG}" ]] || {
    echo "ERROR: S24D1R1 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R1_DESIGN}" ]] || {
    echo "ERROR: S24D1R1 design missing" >&2
    return 1
  }
  stage4_2r3c3t13s24d1_validate_common
}

stage4_2r3c3t13s24d1r1_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R1_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r1_geometry_restoring_search_${stamp}"
}

stage4_2r3c3t13s24d1r1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
