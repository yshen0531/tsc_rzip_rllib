#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R14R4_CONFIG="${STAGE4_2R3C3T13S24D1R14R4_CONFIG:-${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R14R4_PYTHON="${STAGE4_2R3C3T13S24D1R14R4_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R14R4_WORKERS="${STAGE4_2R3C3T13S24D1R14R4_WORKERS:-96}"
STAGE4_2R3C3T13S24D1R14R4_BACKEND="${STAGE4_2R3C3T13S24D1R14R4_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R14R4_COMMAND="${STAGE4_2R3C3T13S24D1R14R4_COMMAND:-offline}"
STAGE4_2R3C3T13S24D1R14R4_RESUME="${STAGE4_2R3C3T13S24D1R14R4_RESUME:-0}"
STAGE4_2R3C3T13S24D1R14R4_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R4_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r4_runs}"
STAGE4_2R3C3T13S24D1R14R4_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14R4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R14R4_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14R4_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R14R4_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r14r4_${UID:-0}}"

STAGE4_2R3C3T13S24D1R13_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R13_PYTHON="${STAGE4_2R3C3T13S24D1R14R4_PYTHON}"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r13_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r13_shell_common.sh"

stage4_2r3c3t13s24d1r14r4_find_source_d1r13() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r13_runs/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel_20260804_df3910f_v1"
  [[ -f "${path}/final_result.json" ]] || { echo "ERROR: exact immutable D1R13 final result missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel/stage_state.json" ]] || { echo "ERROR: exact immutable D1R13 state missing" >&2; return 1; }
  [[ -d "${path}/stage4_2r3c3t13s24d1r13_zero_increment_deconfounding_sentinel/raw" ]] || { echo "ERROR: exact immutable D1R13 raw missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r4_find_source_d1r13_audit() {
  local run
  run="$(stage4_2r3c3t13s24d1r14r4_find_source_d1r13)"
  [[ -f "${run}/server_independent_forensics_v1.json" ]] || { echo "ERROR: exact D1R13 independent audit missing" >&2; return 1; }
  printf '%s\n' "${run}/server_independent_forensics_v1.json"
}

stage4_2r3c3t13s24d1r14r4_find_source_r1a() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r1a_audits/stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_20260804_b8040b6_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r1a_detailed_v1.json" ]] || { echo "ERROR: exact immutable R1A detailed output missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r1a_summary_v1.json" ]] || { echo "ERROR: exact immutable R1A summary missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r1a_manifest_v1.json" ]] || { echo "ERROR: exact immutable R1A manifest missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r4_find_source_r2() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r2_runs/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel_20260804_ca2815a_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r2_mixed_basis_signed_excitation_sentinel/analysis/final_result.json" ]] || { echo "ERROR: exact immutable R2 final result missing" >&2; return 1; }
  [[ -f "${path}/server_independent_forensics_v1.json" ]] || { echo "ERROR: exact immutable R2 independent audit missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r4_find_source_r3_initial() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r3_audits/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_85012c1_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r3_primary_v1.json" ]] || { echo "ERROR: exact R3 initial primary output missing" >&2; return 1; }
  [[ -f "${path}/stage4_2r3c3t13s24d1r14r3_independent_v1.json" ]] || { echo "ERROR: exact R3 initial independent output missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r4_find_source_r3_corrected() {
  local path
  path="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r14r3_audits/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_20260804_ca49a36_v2"
  [[ -f "${path}/compact_evidence_manifest_v2.json" ]] || { echo "ERROR: exact corrected R3 compact manifest missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r14r4_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R14R4_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R14R4_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r14r4_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R14R4_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R14R4_CONFIG}" ]] || { echo "ERROR: D1R14R4 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14R4_WORKERS}" == 96 ]] || { echo "ERROR: D1R14R4 capacity is frozen at 96" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R14R4_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R14R4_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R14R4_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R14R4_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R14R4_COMMAND}" in
    offline|run|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r14r4_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R14R4_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24D1R13_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14R4_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24D1R13_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14R4_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24d1r13_export_runtime
}
