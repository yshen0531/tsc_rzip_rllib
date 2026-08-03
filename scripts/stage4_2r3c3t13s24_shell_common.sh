#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24_PROJECT_DIR="${STAGE4_2R3C3T13S24_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24_CONFIG="${STAGE4_2R3C3T13S24_CONFIG:-${STAGE4_2R3C3T13S24_PROJECT_DIR}/configs/stage4_2r3c3t13s24_sequential_transition_identification_370ms.json}"
STAGE4_2R3C3T13S24_PYTHON="${STAGE4_2R3C3T13S24_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24_WORKERS="${STAGE4_2R3C3T13S24_WORKERS:-128}"
STAGE4_2R3C3T13S24_BACKEND="${STAGE4_2R3C3T13S24_BACKEND:-ray}"
STAGE4_2R3C3T13S24_COMMAND="${STAGE4_2R3C3T13S24_COMMAND:-offline}"
STAGE4_2R3C3T13S24_RESUME="${STAGE4_2R3C3T13S24_RESUME:-0}"
STAGE4_2R3C3T13S24_OUTPUT_ROOT="${STAGE4_2R3C3T13S24_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24_PROJECT_DIR}/stage4_2r3c3t13s24_runs}"
STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24_${UID:-0}}"

STAGE4_2R3C3T13S21_PROJECT_DIR="${STAGE4_2R3C3T13S24_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s21_shell_common.sh
source "${STAGE4_2R3C3T13S24_PROJECT_DIR}/scripts/stage4_2r3c3t13s21_shell_common.sh"

stage4_2r3c3t13s24_find_source_s21() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24_PROJECT_DIR}/stage4_2r3c3t13s21_runs/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_20260803_024821_98dc353"
  expected="01ebdfab81d8d24f96d222846a71ee23c49daafbe93c7fabe2c49cb0a2e60fd1"
  [[ -f "${path}/stage4_2r3c3t13s21_state.json" ]] || { echo "ERROR: exact immutable S21 state missing" >&2; return 1; }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s21_state.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || { echo "ERROR: immutable S21 state SHA-256 mismatch" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24_find_source_s23r1() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24_PROJECT_DIR}/stage4_2r3c3t13s23r1_audits/stage4_2r3c3t13s23r1_amplitude_coded_preflight_20260803_101707"
  expected="305c4003fe5572bd6434541fe983e77422c5e44af46a925bdca6d06b9b4f2177"
  [[ -f "${path}/stage4_2r3c3t13s23r1_summary_v1.json" ]] || { echo "ERROR: exact immutable S23R1 output missing" >&2; return 1; }
  actual="$(sha256sum "${path}/stage4_2r3c3t13s23r1_summary_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || { echo "ERROR: immutable S23R1 summary SHA-256 mismatch" >&2; return 1; }
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24_OUTPUT_ROOT}/stage4_2r3c3t13s24_sequential_transition_identification_${stamp}"
}

stage4_2r3c3t13s24_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24_CONFIG}" ]] || { echo "ERROR: S24 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24_WORKERS}" == 128 ]] || { echo "ERROR: S24 capacity is frozen at 128" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24_BACKEND}" == ray || "${STAGE4_2R3C3T13S24_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24_RESUME}" == 0 || "${STAGE4_2R3C3T13S24_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24_COMMAND}" in
    offline|training-baseline|training-sequence|fit-training|calibration-baseline|calibration-sequence|calibrate|holdout-baseline|holdout-sequence|finalize|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S21_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24_TSC_RUN_ROOT}"
  stage4_2r3c3t13s21_export_runtime
}
