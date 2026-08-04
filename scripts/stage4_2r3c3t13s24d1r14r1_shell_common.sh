#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14R1_PYTHON="${STAGE4_2R3C3T13S24D1R14R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14R1_CONFIG="${STAGE4_2R3C3T13S24D1R14R1_CONFIG:-${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1.json}"
STAGE4_2R3C3T13S24D1R14R1_DESIGN="${STAGE4_2R3C3T13S24D1R14R1_DESIGN:-${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S24D1R14R1_POOLED_MIXED_BASIS_PREFLIGHT_DESIGN.md}"
STAGE4_2R3C3T13S24D1R14R1_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R1_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r1_audits}"

stage4_2r3c3t13s24d1r14r1_validate_common() {
  [[ "${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]] || {
    echo "ERROR: unexpected remote project path" >&2
    return 1
  }
  [[ -x "${STAGE4_2R3C3T13S24D1R14R1_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R1_CONFIG}" ]] || {
    echo "ERROR: D1R14R1 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R1_DESIGN}" ]] || {
    echo "ERROR: D1R14R1 design missing" >&2
    return 1
  }
}

stage4_2r3c3t13s24d1r14r1_new_output_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14R1_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R14R1_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_${stamp}"
}

stage4_2r3c3t13s24d1r14r1_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14R1_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
