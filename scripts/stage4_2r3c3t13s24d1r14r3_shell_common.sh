#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14R3_PYTHON="${STAGE4_2R3C3T13S24D1R14R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14R3_CONFIG="${STAGE4_2R3C3T13S24D1R14R3_CONFIG:-${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_v1.json}"
STAGE4_2R3C3T13S24D1R14R3_DESIGN="${STAGE4_2R3C3T13S24D1R14R3_DESIGN:-${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SIGN_SPLIT_RESPONSE_FEASIBILITY_DESIGN.md}"
STAGE4_2R3C3T13S24D1R14R3_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R3_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r3_audits}"

# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r2_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r2_shell_common.sh"

stage4_2r3c3t13s24d1r14r3_validate_common() {
  [[ "${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]] || {
    echo "ERROR: unexpected remote project path" >&2
    return 1
  }
  [[ -x "${STAGE4_2R3C3T13S24D1R14R3_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R3_CONFIG}" ]] || {
    echo "ERROR: D1R14R3 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R3_DESIGN}" ]] || {
    echo "ERROR: D1R14R3 design missing" >&2
    return 1
  }
}

stage4_2r3c3t13s24d1r14r3_source_r2() {
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r2_runs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1"
}

stage4_2r3c3t13s24d1r14r3_new_output() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14R3_OUTPUT_ROOT}"
  printf '%s/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_%s\n' \
    "${STAGE4_2R3C3T13S24D1R14R3_OUTPUT_ROOT}" "$(date -u +%Y%m%d_%H%M%S)"
}

stage4_2r3c3t13s24d1r14r3_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14R3_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}

