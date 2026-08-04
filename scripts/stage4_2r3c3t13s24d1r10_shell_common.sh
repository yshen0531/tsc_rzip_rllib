#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R10_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R10_CONFIG="${STAGE4_2R3C3T13S24D1R10_CONFIG:-${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R10_PYTHON="${STAGE4_2R3C3T13S24D1R10_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R10_WORKERS="${STAGE4_2R3C3T13S24D1R10_WORKERS:-96}"
STAGE4_2R3C3T13S24D1R10_BACKEND="${STAGE4_2R3C3T13S24D1R10_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R10_COMMAND="${STAGE4_2R3C3T13S24D1R10_COMMAND:-all}"
STAGE4_2R3C3T13S24D1R10_RESUME="${STAGE4_2R3C3T13S24D1R10_RESUME:-0}"
STAGE4_2R3C3T13S24D1R10_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R10_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}/stage4_2r3c3t13s24d1r10_runs}"
STAGE4_2R3C3T13S24D1R10_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R10_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R10_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R10_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R10_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r10_${UID:-0}}"

STAGE4_2R3C3T13S24_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s24_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}/scripts/stage4_2r3c3t13s24_shell_common.sh"

stage4_2r3c3t13s24d1r10_source_d1r9() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}/stage4_2r3c3t13s24d1r9_audits/stage4_2r3c3t13s24d1r9_central_row_replacement_preflight_20260803_a4547d5_v1"
  expected="93ee3961dc5a439a6eec76c84d87b5535e3d4c84fc4b0173ad9703a6344e906e"
  [[ -f "${path}/stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json" ]] || return 1
  actual="$(sha256sum "${path}/stage4_2r3c3t13s24d1r9_d1r10_candidate_specs_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r10_source_d1r9_log() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}/stage4_2r3c3t13s24d1r9_run_a4547d5_v1.log"
  expected="612b9656d9f8715f99de3881df7b9632e640922a86ca89f2516f3f2bd16cfe01"
  [[ -f "${path}" ]] || return 1
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r10_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R10_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R10_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r10_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R10_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R10_CONFIG}" ]] || { echo "ERROR: D1R10 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R10_WORKERS}" == 96 ]] || { echo "ERROR: D1R10 capacity is frozen at 96" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R10_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R10_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R10_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R10_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R10_COMMAND}" in
    offline|rollout|postprocess|all) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r10_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R10_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R10_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R10_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24_export_runtime
}
