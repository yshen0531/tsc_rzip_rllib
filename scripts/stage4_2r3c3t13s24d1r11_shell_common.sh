#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R11_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R11_CONFIG="${STAGE4_2R3C3T13S24D1R11_CONFIG:-${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_370ms.json}"
STAGE4_2R3C3T13S24D1R11_PYTHON="${STAGE4_2R3C3T13S24D1R11_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R11_WORKERS="${STAGE4_2R3C3T13S24D1R11_WORKERS:-128}"
STAGE4_2R3C3T13S24D1R11_BACKEND="${STAGE4_2R3C3T13S24D1R11_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R11_COMMAND="${STAGE4_2R3C3T13S24D1R11_COMMAND:-offline}"
STAGE4_2R3C3T13S24D1R11_RESUME="${STAGE4_2R3C3T13S24D1R11_RESUME:-0}"
STAGE4_2R3C3T13S24D1R11_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R11_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24d1r11_runs}"
STAGE4_2R3C3T13S24D1R11_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R11_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R11_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R11_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R11_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r11_${UID:-0}}"

STAGE4_2R3C3T13S21_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s21_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/scripts/stage4_2r3c3t13s21_shell_common.sh"

stage4_2r3c3t13s24d1r11_find_source_s21() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s21_runs/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353"
  expected="01ebdfab81d8d24f96d222846a71ee23c49daafbe93c7fabe2c49cb0a2e60fd1"
  [[ -f "${path}/stage4_2r3c3t13s21_state.json" ]] || { echo "ERROR: exact immutable S21 state missing" >&2; return 1; }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s21_state.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || { echo "ERROR: immutable S21 state SHA-256 mismatch" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_s23r1() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s23r1_audits/stage4_2r3c3t13s23r1_amplitude_coded_preflight_20260803_101707"
  expected="305c4003fe5572bd6434541fe983e77422c5e44af46a925bdca6d06b9b4f2177"
  [[ -f "${path}/stage4_2r3c3t13s23r1_summary_v1.json" ]] || { echo "ERROR: exact immutable S23R1 output missing" >&2; return 1; }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s23r1_summary_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || { echo "ERROR: immutable S23R1 summary SHA-256 mismatch" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_s24() {
  local path
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24_runs/stage4_2r3c3t13s24_sequential_transition_identification_20260803_111226_0c71836"
  [[ -f "${path}/stage4_2r3c3t13s24_sequential_transition_identification/stage_state.json" ]] || { echo "ERROR: immutable S24 source missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_d1r9_v1() {
  local path
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24d1r9_audits/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json" ]] || { echo "ERROR: immutable D1R9 v1 source missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_d1r9_v2() {
  local path
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24d1r9_audits/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v2"
  [[ -f "${path}/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_v1.json" ]] || { echo "ERROR: immutable D1R9 v2 source missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_d1r10() {
  local path
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24d1r10_runs/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_20260804_2ece6df_v1"
  [[ -f "${path}/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel/final_result.json" ]] || { echo "ERROR: immutable D1R10 source missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_find_source_d1r10_audit() {
  local path
  path="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}/stage4_2r3c3t13s24d1r10_audits/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_20260804_2ece6df_v1/stage4_2r3c3t13s24d1r10_server_audit_hotfix_v3.json"
  [[ -f "${path}" ]] || { echo "ERROR: immutable D1R10 audit missing" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r11_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R11_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R11_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_${stamp}"
}

stage4_2r3c3t13s24d1r11_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R11_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R11_CONFIG}" ]] || { echo "ERROR: S24D1R11 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R11_WORKERS}" == 128 ]] || { echo "ERROR: S24D1R11 capacity is frozen at 128" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R11_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R11_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R11_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R11_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R11_COMMAND}" in
    offline|training-baseline|training-sequence|fit-training|calibration-baseline|calibration-sequence|calibrate|holdout-baseline|holdout-sequence|finalize|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r11_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R11_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R11_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S21_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R11_TSC_RUN_ROOT}"
  stage4_2r3c3t13s21_export_runtime
}
