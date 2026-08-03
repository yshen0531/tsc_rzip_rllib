#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R8_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R8_CONFIG="${STAGE4_2R3C3T13S24D1R8_CONFIG:-${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r8_real_tsc_safety_sentinel_370ms.json}"
STAGE4_2R3C3T13S24D1R8_PYTHON="${STAGE4_2R3C3T13S24D1R8_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R8_WORKERS="${STAGE4_2R3C3T13S24D1R8_WORKERS:-96}"
STAGE4_2R3C3T13S24D1R8_BACKEND="${STAGE4_2R3C3T13S24D1R8_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R8_COMMAND="${STAGE4_2R3C3T13S24D1R8_COMMAND:-all}"
STAGE4_2R3C3T13S24D1R8_RESUME="${STAGE4_2R3C3T13S24D1R8_RESUME:-0}"
STAGE4_2R3C3T13S24D1R8_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R8_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}/stage4_2r3c3t13s24d1r8_runs}"
STAGE4_2R3C3T13S24D1R8_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R8_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R8_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R8_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R8_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r8_${UID:-0}}"

STAGE4_2R3C3T13S24_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s24_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}/scripts/stage4_2r3c3t13s24_shell_common.sh"

stage4_2r3c3t13s24d1r8_source_d1r7() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}/stage4_2r3c3t13s24d1r7_audits/stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight_20260803_212200_0c2311a_v1"
  expected="76075e12a411dbd4b0c210cc2e91a8978cb4de908b6f88a2c1ecd9cc44b279f7"
  [[ -f "${path}/stage4_2r3c3t13s24d1r7_candidate_specs_v1.json" ]] || return 1
  actual="$(sha256sum "${path}/stage4_2r3c3t13s24d1r7_candidate_specs_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r8_source_d1r7_log() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r7_official_20260803_212200_0c2311a_v1.log"
  expected="b69bd7464cb5c25225a280ed98c1ccd6be75d4b472bdca84b9724cfd82893325"
  [[ -f "${path}" ]] || return 1
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r8_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R8_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R8_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r8_temporal_basis_substitution_safety_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r8_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R8_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R8_CONFIG}" ]] || { echo "ERROR: D1R8 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R8_WORKERS}" == 96 ]] || { echo "ERROR: D1R8 capacity is frozen at 96" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R8_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R8_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R8_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R8_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R8_COMMAND}" in
    offline|rollout|postprocess|all) ;;
    *) return 1 ;;
  esac
}

stage4_2r3c3t13s24d1r8_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R8_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R8_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R8_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24_export_runtime
}
