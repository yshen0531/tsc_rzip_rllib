#!/usr/bin/env bash
set -euo pipefail

STAGE4_2R3C3T13S24D1R4_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
STAGE4_2R3C3T13S24D1R4_CONFIG="${STAGE4_2R3C3T13S24D1R4_CONFIG:-${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_350ms.json}"
STAGE4_2R3C3T13S24D1R4_PYTHON="${STAGE4_2R3C3T13S24D1R4_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
STAGE4_2R3C3T13S24D1R4_WORKERS="${STAGE4_2R3C3T13S24D1R4_WORKERS:-9}"
STAGE4_2R3C3T13S24D1R4_BACKEND="${STAGE4_2R3C3T13S24D1R4_BACKEND:-ray}"
STAGE4_2R3C3T13S24D1R4_COMMAND="${STAGE4_2R3C3T13S24D1R4_COMMAND:-all}"
STAGE4_2R3C3T13S24D1R4_RESUME="${STAGE4_2R3C3T13S24D1R4_RESUME:-0}"
STAGE4_2R3C3T13S24D1R4_OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R4_OUTPUT_ROOT:-${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r4_runs}"
STAGE4_2R3C3T13S24D1R4_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R4_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R4_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R4_TSC_WORKSPACE_ROOT}/episode_runs}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r4_${UID:-0}}"

STAGE4_2R3C3T13S24D1R2_PROJECT_DIR="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r2_shell_common.sh
source "${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r2_shell_common.sh"

stage4_2r3c3t13s24d1r4_source_d1r2_run() {
  local path
  path="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r2_runs/stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2"
  [[ -d "${path}/stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel/raw" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r4_source_d1r3_output() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/stage4_2r3c3t13s24d1r3_audits/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_20260803_170619_93afef5"
  expected="5c26680bc1483148a95cca9a06bb4eb546d01e385af6a907941d4b74b82a0d1a"
  [[ -f "${path}/stage4_2r3c3t13s24d1r3_candidate_sentinel_specs_v1.json" ]] || return 1
  actual="$(sha256sum "${path}/stage4_2r3c3t13s24d1r3_candidate_sentinel_specs_v1.json" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r4_source_d1r3_primary_log() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/logs/stage4_2r3c3t13s24d1r3_offline_20260803_170619_93afef5.log"
  expected="d6c863bcee14b324122e5b0b4ed50db3d54a9187acd2fbf002598e26596a4fa3"
  [[ -f "${path}" ]] || return 1
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r4_source_d1r3_repeat_log() {
  local path expected actual
  path="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}/logs/stage4_2r3c3t13s24d1r3_offline_20260803_170619_93afef5_repeat.log"
  expected="8f325f4bea1866af1a5e8a6b6617b456ca511b511a22489b2bb831f3865ebcec"
  [[ -f "${path}" ]] || return 1
  actual="$(sha256sum "${path}" | awk '{print $1}')"
  [[ "${actual}" == "${expected}" ]] || return 1
  printf '%s\n' "${path}"
}

stage4_2r3c3t13s24d1r4_new_run_dir() {
  mkdir -p "${STAGE4_2R3C3T13S24D1R4_OUTPUT_ROOT}"
  local stamp
  stamp="$(date -u +%Y%m%d_%H%M%S)"
  printf '%s\n' "${STAGE4_2R3C3T13S24D1R4_OUTPUT_ROOT}/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_${stamp}"
}

stage4_2r3c3t13s24d1r4_validate_common() {
  [[ -x "${STAGE4_2R3C3T13S24D1R4_PYTHON}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; return 1; }
  [[ -f "${STAGE4_2R3C3T13S24D1R4_CONFIG}" ]] || { echo "ERROR: D1R4 config missing" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R4_WORKERS}" == 9 ]] || { echo "ERROR: D1R4 capacity is frozen at 9" >&2; return 1; }
  [[ "${STAGE4_2R3C3T13S24D1R4_BACKEND}" == ray || "${STAGE4_2R3C3T13S24D1R4_BACKEND}" == serial ]] || return 1
  [[ "${STAGE4_2R3C3T13S24D1R4_RESUME}" == 0 || "${STAGE4_2R3C3T13S24D1R4_RESUME}" == 1 ]] || return 1
  case "${STAGE4_2R3C3T13S24D1R4_COMMAND}" in offline|rollout|postprocess|all) ;; *) return 1 ;; esac
}

stage4_2r3c3t13s24d1r4_export_runtime() {
  export PROJECT_DIR="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}"
  export PYTHONPATH="${STAGE4_2R3C3T13S24D1R4_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  STAGE4_2R3C3T13S24_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R4_TSC_WORKSPACE_ROOT}"
  STAGE4_2R3C3T13S24_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R4_TSC_RUN_ROOT}"
  stage4_2r3c3t13s24_export_runtime
}
