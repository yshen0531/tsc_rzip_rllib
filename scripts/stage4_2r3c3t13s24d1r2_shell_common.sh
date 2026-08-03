#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R2_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R2_CONFIG="${STAGE4_2R3C3T13S24D1R2_CONFIG:-${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R2_PYTHON="${STAGE4_2R3C3T13S24D1R2_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R2_WORKERS="${STAGE4_2R3C3T13S24D1R2_WORKERS:-54}"
STAGE4_2R3C3T13S24D1R2_BACKEND="${STAGE4_2R3C3T13S24D1R2_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R2_COMMAND="${STAGE4_2R3C3T13S24D1R2_COMMAND:-all}"
STAGE4_2R3C3T13S24D1R2_RESUME="${STAGE4_2R3C3T13S24D1R2_RESUME:-0}"
STAGE4_2R3C3T13S24D1R2_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R2_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}/stage4_2r3c3t13s24d1r2_runs}"
STAGE4_2R3C3T13S24D1R2_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R2_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R2_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R2_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r2_${UID:-0}}"

STAGE4_2R3C3T13S24_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s24_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}/scripts/stage4_2r3c3t13s24_shell_common.sh"

stage4_2r3c3t13s24d1r2_source_d1r1() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}/stage4_2r3c3t13s24d1r1_audits/stage4_2r3c3t13s24d1r1_geometry_restoring_search_20260803_145327"
  expected="61574900383ae91083173065561ea8f2a80a96a4c6935f3a965ef7ce43215c46"
  [[ -f "${path}/stage4_2r3c3t13s24d1r1_selected_sentinel_specs_v1.json" ]] || return 1
  actual="$(sha256sum "${path}/stage4_2r3c3t13s24d1r1_selected_sentinel_specs_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r2_source_d1r1_log() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r1_offline_20260803_145327.log"
  expected="89eb453af423ed9a7b4cb48122e0228b99ec1a8b3335865f7d6cf4f1bb59eb2e"
  [[ -f "${path}" ]] || return 1
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r2_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R2_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R2_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r2_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R2_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R2_CONFIG}" ]] || { echo "ERROR: D1R2 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R2_WORKERS}" == 54 ]] || { echo "ERROR: D1R2 capacity is frozen at 54" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R2_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R2_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R2_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R2_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R2_COMMAND}" in
    offline|rollout|postprocess|all) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r2_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R2_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R2_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R2_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24_export_runtime
}
