#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_3_shell_common.sh"
stage33_project_init
stage33_find_python
command -v setsid >/dev/null 2>&1 || stage33_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage3_3_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage3_3_target_conditioned_mpc_${STAMP}.log"
if [[ -n "${STAGE3_3_RUN_DIR:-}" ]]; then RUN_DIR="$(stage33_abspath "${STAGE3_3_RUN_DIR}")"
else RUN_DIR="${PROJECT_DIR}/stage3_3_runs/stage3_3_target_conditioned_receding_horizon_mpc_250ms_${STAMP}"; fi
RESUME="${STAGE3_3_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage33_die "STAGE3_3_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_3_state.json" ]] || stage33_die "resume state missing: ${RUN_DIR}/stage3_3_state.json"
  stage33_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage33_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage33_detect_source_stage32
CONFIG="${STAGE3_3_CONFIG:-${PROJECT_DIR}/configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json}"
CONFIG="$(stage33_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage33_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE3_3_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE3_3_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage3_3_$(id -u)}"
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE3_3_RUN_DIR="${RUN_DIR}" STAGE3_3_RESUME="${RESUME}" STAGE3_3_CONFIG="${CONFIG}" \
  STAGE3_3_COMMAND="${STAGE3_3_COMMAND:-all}" STAGE3_3_BACKEND="${STAGE3_3_BACKEND:-ray}" \
  SOURCE_STAGE3_2_RUN="${SOURCE_STAGE3_2_RUN}" \
  STAGE3_3_WORKERS="${STAGE3_3_WORKERS:-96}" STAGE3_3_TSC_WORKSPACE_ROOT="${WORKSPACE}" \
  STAGE3_3_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  bash "${PROJECT_DIR}/run_stage3_3_target_conditioned_mpc_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage3_3_runs/stage3_3_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_3_target_conditioned_mpc.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_3_target_conditioned_mpc.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_3_runs/latest_stage3_3_run.txt"
echo "[Stage3.3] pid=${PID}"
echo "[Stage3.3] run_dir=${RUN_DIR}"
echo "[Stage3.3] log=${LOG_FILE}"
echo "[Stage3.3] follow: tail -f \"${LOG_FILE}\""
