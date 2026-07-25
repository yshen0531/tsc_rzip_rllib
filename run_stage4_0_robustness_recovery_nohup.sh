#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_0_shell_common.sh"
stage40_project_init
stage40_find_python
command -v setsid >/dev/null 2>&1 || stage40_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage4_0_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_0_robustness_recovery_${STAMP}.log"
if [[ -n "${STAGE4_RUN_DIR:-${STAGE4_0_RUN_DIR:-}}" ]]; then RUN_DIR="$(stage40_abspath "${STAGE4_RUN_DIR:-${STAGE4_0_RUN_DIR}}")"; else RUN_DIR="${PROJECT_DIR}/stage4_0_runs/stage4_0_robustness_recovery_350ms_${STAMP}"; fi
RESUME="${STAGE4_RESUME:-${STAGE4_0_RESUME:-0}}"
case "${RESUME}" in 0|1) ;; *) stage40_die "STAGE4_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_0_state.json" ]] || stage40_die "resume state missing: ${RUN_DIR}/stage4_0_state.json"
  stage40_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then stage40_die "fresh run directory is not empty: ${RUN_DIR}"; fi
stage40_detect_source
CONFIG="${STAGE4_CONFIG:-${STAGE4_0_CONFIG:-${PROJECT_DIR}/configs/stage4_0_robustness_recovery_350ms.json}}"
CONFIG="$(stage40_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage40_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE4_TSC_WORKSPACE_ROOT:-${STAGE4_0_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}}"
RUN_ROOT="${STAGE4_TSC_RUN_ROOT:-${STAGE4_0_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage4_0_$(id -u)}"
nohup setsid env PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE4_RUN_DIR="${RUN_DIR}" STAGE4_0_RUN_DIR="${RUN_DIR}" STAGE4_RESUME="${RESUME}" STAGE4_0_RESUME="${RESUME}" STAGE4_CONFIG="${CONFIG}" STAGE4_0_CONFIG="${CONFIG}" \
  STAGE4_COMMAND="${STAGE4_COMMAND:-${STAGE4_0_COMMAND:-all}}" STAGE4_0_COMMAND="${STAGE4_COMMAND:-${STAGE4_0_COMMAND:-all}}" STAGE4_BACKEND="${STAGE4_BACKEND:-${STAGE4_0_BACKEND:-ray}}" STAGE4_0_BACKEND="${STAGE4_BACKEND:-${STAGE4_0_BACKEND:-ray}}" \
  SOURCE_STAGE3_4_RUN="${SOURCE_STAGE3_4_RUN}" STAGE4_WORKERS="${STAGE4_WORKERS:-${STAGE4_0_WORKERS:-192}}" STAGE4_0_WORKERS="${STAGE4_WORKERS:-${STAGE4_0_WORKERS:-192}}" \
  STAGE4_TSC_WORKSPACE_ROOT="${WORKSPACE}" STAGE4_0_TSC_WORKSPACE_ROOT="${WORKSPACE}" STAGE4_TSC_RUN_ROOT="${RUN_ROOT}" STAGE4_0_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  STAGE4_START_FOLDERS="${STAGE4_START_FOLDERS:-}" \
  "${PROJECT_DIR}/run_stage4_0_robustness_recovery_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage4_0_runs/stage4_0_driver.pid"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_0_runs/latest_stage4_0_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_0_robustness_recovery.log"
echo "[Stage4.0] pid=${PID}"
echo "[Stage4.0] run_dir=${RUN_DIR}"
echo "[Stage4.0] log=${LOG_FILE}"
