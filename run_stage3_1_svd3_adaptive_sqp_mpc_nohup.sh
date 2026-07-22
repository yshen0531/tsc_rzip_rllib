#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_1_shell_common.sh"
stage31_project_init
stage31_find_python
command -v setsid >/dev/null 2>&1 || stage31_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage3_1_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage3_1_adaptive_sqp_mpc_${STAMP}.log"
if [[ -n "${STAGE3_1_RUN_DIR:-}" ]]; then RUN_DIR="$(stage31_abspath "${STAGE3_1_RUN_DIR}")"
else RUN_DIR="${PROJECT_DIR}/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_${STAMP}"; fi
RESUME="${STAGE3_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage31_die "STAGE3_1_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_1_state.json" ]] || stage31_die "resume state missing: ${RUN_DIR}/stage3_1_state.json"
  stage31_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage31_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage31_detect_source_stage30
CONFIG="${STAGE3_1_CONFIG:-${PROJECT_DIR}/configs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms.json}"
CONFIG="$(stage31_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage31_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE3_1_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE3_1_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage3_1_$(id -u)}"
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE3_1_RUN_DIR="${RUN_DIR}" STAGE3_1_RESUME="${RESUME}" STAGE3_1_CONFIG="${CONFIG}" \
  STAGE3_1_COMMAND="${STAGE3_1_COMMAND:-all}" STAGE3_1_BACKEND="${STAGE3_1_BACKEND:-ray}" \
  SOURCE_STAGE3_0_RUN="${SOURCE_STAGE3_0_RUN}" SOURCE_STAGE2_2_RUN="${SOURCE_STAGE2_2_RUN:-}" \
  STAGE3_1_WORKERS="${STAGE3_1_WORKERS:-96}" STAGE3_1_TSC_WORKSPACE_ROOT="${WORKSPACE}" \
  STAGE3_1_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  bash "${PROJECT_DIR}/run_stage3_1_svd3_adaptive_sqp_mpc_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage3_1_runs/stage3_1_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_1_adaptive_sqp_mpc.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_1_adaptive_sqp_mpc.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_1_runs/latest_stage3_1_run.txt"
echo "[Stage3.1] pid=${PID}"
echo "[Stage3.1] run_dir=${RUN_DIR}"
echo "[Stage3.1] log=${LOG_FILE}"
echo "[Stage3.1] follow: tail -f \"${LOG_FILE}\""
