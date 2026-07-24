#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_4_shell_common.sh"
stage34_project_init
stage34_find_python
command -v setsid >/dev/null 2>&1 || stage34_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage3_4_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage3_4_late_arrival_continuation_mpc_${STAMP}.log"
if [[ -n "${STAGE3_4_RUN_DIR:-}" ]]; then RUN_DIR="$(stage34_abspath "${STAGE3_4_RUN_DIR}")"
else RUN_DIR="${PROJECT_DIR}/stage3_4_runs/stage3_4_late_arrival_continuation_mpc_350ms_${STAMP}"; fi
RESUME="${STAGE3_4_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage34_die "STAGE3_4_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_4_state.json" ]] || stage34_die "resume state missing: ${RUN_DIR}/stage3_4_state.json"
  stage34_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage34_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage34_detect_source_stage33
CONFIG="${STAGE3_4_CONFIG:-${PROJECT_DIR}/configs/stage3_4_late_arrival_continuation_mpc_350ms.json}"
CONFIG="$(stage34_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage34_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE3_4_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE3_4_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage3_4_$(id -u)}"
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE3_4_RUN_DIR="${RUN_DIR}" STAGE3_4_RESUME="${RESUME}" STAGE3_4_CONFIG="${CONFIG}" \
  STAGE3_4_COMMAND="${STAGE3_4_COMMAND:-all}" STAGE3_4_BACKEND="${STAGE3_4_BACKEND:-ray}" \
  SOURCE_STAGE3_3_RUN="${SOURCE_STAGE3_3_RUN}" \
  STAGE3_4_WORKERS="${STAGE3_4_WORKERS:-96}" STAGE3_4_TSC_WORKSPACE_ROOT="${WORKSPACE}" \
  STAGE3_4_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  "${PROJECT_DIR}/run_stage3_4_late_arrival_continuation_mpc_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage3_4_runs/stage3_4_driver.pid"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_4_runs/latest_stage3_4_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_4_late_arrival_continuation_mpc.log"
echo "[Stage3.4] pid=${PID}"
echo "[Stage3.4] run_dir=${RUN_DIR}"
echo "[Stage3.4] log=${LOG_FILE}"
