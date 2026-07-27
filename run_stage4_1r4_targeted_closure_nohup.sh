#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r4_shell_common.sh"
stage41r4_project_init
stage41r4_find_python
command -v setsid >/dev/null 2>&1 || stage41r4_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage4_1r4_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r4_targeted_closure_${STAMP}.log"
if [[ -n "${STAGE4_1R4_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r4_abspath "${STAGE4_1R4_RUN_DIR}")"
else
  RUN_DIR="${PROJECT_DIR}/stage4_1r4_runs/stage4_1r4_targeted_closure_370ms_${STAMP}"
fi
RESUME="${STAGE4_1R4_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r4_die "STAGE4_1R4_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r4_state.json" ]] || stage41r4_die "resume state missing: ${RUN_DIR}/stage4_1r4_state.json"
  stage41r4_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage41r4_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage41r4_detect_source
CONFIG="${STAGE4_1R4_CONFIG:-${PROJECT_DIR}/configs/stage4_1r4_targeted_closure_370ms.json}"
CONFIG="$(stage41r4_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r4_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE4_1R4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE4_1R4_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage4_1r4_$(id -u)}"
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE4_1R4_RUN_DIR="${RUN_DIR}" STAGE4_1R4_RESUME="${RESUME}" STAGE4_1R4_CONFIG="${CONFIG}" \
  STAGE4_1R4_COMMAND="${STAGE4_1R4_COMMAND:-all}" STAGE4_1R4_BACKEND="${STAGE4_1R4_BACKEND:-ray}" \
  SOURCE_STAGE4_1R3_RUN="${SOURCE_STAGE4_1R3_RUN}" STAGE4_1R4_WORKERS="${STAGE4_1R4_WORKERS:-${STAGE4_WORKERS:-128}}" \
  STAGE4_1R4_TSC_WORKSPACE_ROOT="${WORKSPACE}" STAGE4_1R4_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  STAGE4_1R4_START_FOLDERS="${STAGE4_1R4_START_FOLDERS:-}" \
  "${PROJECT_DIR}/run_stage4_1r4_targeted_closure_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage4_1r4_runs/stage4_1r4_driver.pid"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r4_runs/latest_stage4_1r4_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_1r4_targeted_closure.log"
echo "[Stage4.1R4] pid=${PID}"
echo "[Stage4.1R4] run_dir=${RUN_DIR}"
echo "[Stage4.1R4] log=${LOG_FILE}"
