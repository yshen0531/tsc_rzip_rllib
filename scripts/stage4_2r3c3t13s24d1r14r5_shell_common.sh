#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14R5_PYTHON="${STAGE4_2R3C3T13S24D1R14R5_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14R5_CONFIG="${STAGE4_2R3C3T13S24D1R14R5_CONFIG:-${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_v1.json}"
STAGE4_2R3C3T13S24D1R14R5_DESIGN="${STAGE4_2R3C3T13S24D1R14R5_DESIGN:-${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}/docs/codex/reports/STAGE4_2R3C3T13S24D1R14R5_GLOBAL_DIRECTION0_GAIN_PREFLIGHT_DESIGN.md}"
STAGE4_2R3C3T13S24D1R14R5_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R5_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r5_audits}"

stage4_2r3c3t13s24d1r14r5_validate_common() {
  [[ "${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]] || {
    echo "ERROR: unexpected remote project path" >&2
    return 1
  }
  [[ -x "${STAGE4_2R3C3T13S24D1R14R5_PYTHON}" ]] || {
    echo "ERROR: server virtualenv Python not executable" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R5_CONFIG}" ]] || {
    echo "ERROR: D1R14R5 config missing" >&2
    return 1
  }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R5_DESIGN}" ]] || {
    echo "ERROR: D1R14R5 design missing" >&2
    return 1
  }
}

stage4_2r3c3t13s24d1r14r5_source_r4() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r4_runs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_20260804_f5b8348_v1"
  [[ -f "${path}/final_result.json" ]] || { echo "ERROR: immutable R4 final missing" >&2; return 1; }
  [[ -f "${path}/server_independent_forensics_v1.json" ]] || { echo "ERROR: immutable R4 independent audit missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r5_source_r2() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r2_runs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel/analysis/final_result.json" ]] || { echo "ERROR: immutable R2 final missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r5_new_output() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14R5_OUTPUT_ROOT}"
  printf '%s/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_%s\n' \
    "${STAGE4_2R3C3T13S24D1R14R5_OUTPUT_ROOT}" "$(date -u +%Y%m%d_%H%M%S)"
}

stage4_2r3c3t13s24d1r14r5_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14R5_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
}
