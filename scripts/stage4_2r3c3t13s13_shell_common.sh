#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S13_PROJECT_DIR="${STAGE4_2R3C3T13S13_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S13_CONFIG="${STAGE4_2R3C3T13S13_CONFIG:-${STAGE4_2R3C3T13S13_PROJECT_DIR}/configs/stage4_2r3c3t13s13_recurrent_sequence_tube_identification_370ms.json}"
STAGE4_2R3C3T13S13_PYTHON="${STAGE4_2R3C3T13S13_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S13_WORKERS="${STAGE4_2R3C3T13S13_WORKERS:-128}"
STAGE4_2R3C3T13S13_BACKEND="${STAGE4_2R3C3T13S13_BACKEND:-ray}"
STAGE4_2R3C3T13S13_COMMAND="${STAGE4_2R3C3T13S13_COMMAND:-offline}"
STAGE4_2R3C3T13S13_RESUME="${STAGE4_2R3C3T13S13_RESUME:-0}"
STAGE4_2R3C3T13S13_OUTPUT_ROOT="${STAGE4_2R3C3T13S13_OUTPUT_ROOT:-${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3c3t13s13_runs}"
STAGE4_2R3C3T13S13_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S13_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S13_TSC_RUN_ROOT="${STAGE4_2R3C3T13S13_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S13_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s13_${UID:-0}}"

STAGE4_2R3C3T11_PROJECT_DIR="${STAGE4_2R3C3T13S13_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t11_shell_common.sh
source "${STAGE4_2R3C3T13S13_PROJECT_DIR}/scripts/stage4_2r3c3t11_shell_common.sh"

stage4_2r3c3t13s13_find_source_r3b() { stage4_2r3c3t11_find_source_r3b; }
stage4_2r3c3t13s13_find_source_r3c3() { stage4_2r3c3t11_find_source_r3c3; }
stage4_2r3c3t13s13_find_source_bank() { stage4_2r3c3t11_find_source_bank; }
stage4_2r3c3t13s13_find_source_t1() { stage4_2r3c3t11_find_source_t1; }
stage4_2r3c3t13s13_find_source_t1_audit() { stage4_2r3c3t11_find_source_t1_audit; }
stage4_2r3c3t13s13_find_t3_controller_bank() { stage4_2r3c3t11_find_t3_controller_bank; }

stage4_2r3c3t13s13_q1_run() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3c3t13s9_runs/stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a"; }
stage4_2r3c3t13s13_q2_run() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3c3t13s5_runs/stage4_2r3c3t13s5_real_20260802_d048686"; }
stage4_2r3c3t13s13_q1_audit() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3c3t13s9_audits/stage4_2r3c3t13s9_unified_postqueue_q1_identification_20260802_2f5138a/stage4_2r3c3t13s9_server_audit.json"; }
stage4_2r3c3t13s13_q2_audit() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3c3t13s5_audits/stage4_2r3c3t13s5_real_20260802_d048686/stage4_2r3c3t13s5_server_audit.json"; }
stage4_2r3c3t13s13_r3b_audit() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3b_audits/stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526/stage4_2r3b_server_audit.json"; }
stage4_2r3c3t13s13_r3b_snapshot_checks() { printf '%s\n' "${STAGE4_2R3C3T13S13_PROJECT_DIR}/stage4_2r3b_audits/stage4_2r3b_confirmatory_hidden_history_initial_state_20260730_115526/stage4_2r3b_snapshot_checks.json"; }

stage4_2r3c3t13s13_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S13_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S13_OUTPUT_ROOT}/stage4_2r3c3t13s13_recurrent_sequence_tube_identification_${stamp}"
}

stage4_2r3c3t13s13_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S13_PYTHON}" ]] || { echo "ERROR: Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S13_CONFIG}" ]] || { echo "ERROR: config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S13_WORKERS}" == "128" ]] || { echo "ERROR: T13S13 capacity is frozen at 128" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S13_BACKEND}" == ray || "${STAGE4_2R3C3T13S13_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S13_RESUME}" == 0 || "${STAGE4_2R3C3T13S13_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S13_COMMAND}" in
    offline|training-baseline|training-probe|fit-training|calibration-baseline|calibration-probe|calibrate|holdout-baseline|holdout-probe|finalize) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s13_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S13_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S13_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  export STAGE4_2R3C3T13S13_WORKERS STAGE4_2R3C3T13S13_TSC_WORKSPACE_ROOT
  export STAGE4_2R3C3T13S13_TSC_RUN_ROOT RAY_TMPDIR
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S13_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T13S13_TSC_RUN_ROOT}"
  stage4_2r3c3t1_export_runtime
}
