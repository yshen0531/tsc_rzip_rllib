#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r5_shell_common.sh"
stage41r5_project_init
stage41r5_find_python
command -v setsid >/dev/null 2>&1 || stage41r5_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage4_1r5_runs"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r5_adaptive_handover_${STAMP}.log"
if [[ -n "${STAGE4_1R5_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r5_abspath "${STAGE4_1R5_RUN_DIR}")"
else
  RUN_DIR="${PROJECT_DIR}/stage4_1r5_runs/stage4_1r5_adaptive_handover_closure_350ms_${STAMP}"
fi
RESUME="${STAGE4_1R5_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r5_die "STAGE4_1R5_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r5_state.json" ]] || stage41r5_die "resume state missing: ${RUN_DIR}/stage4_1r5_state.json"
  stage41r5_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage41r5_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage41r5_detect_source
CONFIG="${STAGE4_1R5_CONFIG:-${PROJECT_DIR}/configs/stage4_1r5_adaptive_handover_closure_350ms.json}"
CONFIG="$(stage41r5_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r5_die "config not found: ${CONFIG}"

WORKSPACE="${STAGE4_1R5_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage4_1r5_$(id -u)}"

nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" \
  TSC_ALL_ROOT="${TSC_ALL_ROOT}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  SOURCE_STAGE4_1R4_RUN="${SOURCE_STAGE4_1R4_RUN}" \
  STAGE4_1R5_RUN_DIR="${RUN_DIR}" \
  STAGE4_1R5_RESUME="${RESUME}" \
  STAGE4_1R5_WORKERS="${STAGE4_1R5_WORKERS:-128}" \
  STAGE4_1R5_CONFIG="${CONFIG}" \
  STAGE4_1R5_COMMAND="${STAGE4_1R5_COMMAND:-all}" \
  STAGE4_1R5_BACKEND="${STAGE4_1R5_BACKEND:-ray}" \
  STAGE4_1R5_TSC_WORKSPACE_ROOT="${WORKSPACE}" \
  STAGE4_1R5_TSC_RUN_ROOT="${RUN_ROOT}" \
  RAY_TMPDIR="${RAY_ROOT}" \
  "${PROJECT_DIR}/run_stage4_1r5_adaptive_handover_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage4_1r5_runs/stage4_1r5_driver.pid"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r5_runs/latest_stage4_1r5_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_1r5_adaptive_handover.log"
echo "[Stage4.1R5] pid=${PID}"
echo "[Stage4.1R5] run_dir=${RUN_DIR}"
echo "[Stage4.1R5] log=${LOG_FILE}"
