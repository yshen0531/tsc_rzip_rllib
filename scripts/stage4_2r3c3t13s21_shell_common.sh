#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S21_PROJECT_DIR="${STAGE4_2R3C3T13S21_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S21_CONFIG="${STAGE4_2R3C3T13S21_CONFIG:-${STAGE4_2R3C3T13S21_PROJECT_DIR}/configs/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_370ms.json}"
STAGE4_2R3C3T13S21_PYTHON="${STAGE4_2R3C3T13S21_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S21_WORKERS="${STAGE4_2R3C3T13S21_WORKERS:-128}"
STAGE4_2R3C3T13S21_BACKEND="${STAGE4_2R3C3T13S21_BACKEND:-ray}"
STAGE4_2R3C3T13S21_COMMAND="${STAGE4_2R3C3T13S21_COMMAND:-offline}"
STAGE4_2R3C3T13S21_RESUME="${STAGE4_2R3C3T13S21_RESUME:-0}"
STAGE4_2R3C3T13S21_OUTPUT_ROOT="${STAGE4_2R3C3T13S21_OUTPUT_ROOT:-${STAGE4_2R3C3T13S21_PROJECT_DIR}/stage4_2r3c3t13s21_runs}"
STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S21_TSC_RUN_ROOT="${STAGE4_2R3C3T13S21_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s21_${UID:-0}}"

STAGE4_2R3C3T13S16_PROJECT_DIR="${STAGE4_2R3C3T13S21_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s16_shell_common.sh
source "${STAGE4_2R3C3T13S21_PROJECT_DIR}/scripts/stage4_2r3c3t13s16_shell_common.sh"

stage4_2r3c3t13s21_find_source_r3b() { stage4_2r3c3t13s16_find_source_r3b; }
stage4_2r3c3t13s21_find_source_r3c3() { stage4_2r3c3t13s16_find_source_r3c3; }
stage4_2r3c3t13s21_find_source_bank() { stage4_2r3c3t13s16_find_source_bank; }
stage4_2r3c3t13s21_find_source_t1() { stage4_2r3c3t13s16_find_source_t1; }
stage4_2r3c3t13s21_find_source_t1_audit() { stage4_2r3c3t13s16_find_source_t1_audit; }
stage4_2r3c3t13s21_find_t3_controller_bank() { stage4_2r3c3t13s16_find_t3_controller_bank; }
stage4_2r3c3t13s21_q1_run() { stage4_2r3c3t13s16_q1_run; }
stage4_2r3c3t13s21_q2_run() { stage4_2r3c3t13s16_q2_run; }
stage4_2r3c3t13s21_q1_audit() { stage4_2r3c3t13s16_q1_audit; }
stage4_2r3c3t13s21_q2_audit() { stage4_2r3c3t13s16_q2_audit; }
stage4_2r3c3t13s21_r3b_audit() { stage4_2r3c3t13s16_r3b_audit; }
stage4_2r3c3t13s21_r3b_snapshot_checks() { stage4_2r3c3t13s16_r3b_snapshot_checks; }

stage4_2r3c3t13s21_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S21_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S21_OUTPUT_ROOT}/stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_${stamp}"
}

stage4_2r3c3t13s21_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S21_PYTHON}" ]] || { echo "ERROR: Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S21_CONFIG}" ]] || { echo "ERROR: config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S21_WORKERS}" == 128 ]] || { echo "ERROR: T13S21 capacity is frozen at 128" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S21_BACKEND}" == ray || "${STAGE4_2R3C3T13S21_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S21_RESUME}" == 0 || "${STAGE4_2R3C3T13S21_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S21_COMMAND}" in
    offline|training-baseline|training-probe|fit-training|calibration-baseline|calibration-probe|calibrate|holdout-baseline|holdout-probe|finalize|postprocess) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s21_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S21_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S21_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S16_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S21_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S16_TSC_RUN_ROOT="${STAGE4_2R3C3T13S21_TSC_RUN_ROOT}"
  stage4_2r3c3t13s16_export_runtime
}
