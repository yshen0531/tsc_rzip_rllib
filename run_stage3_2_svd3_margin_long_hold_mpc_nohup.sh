#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_2_shell_common.sh"
stage32_project_init
stage32_find_python
command -v setsid >/dev/null 2>&1 || stage32_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage3_2_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage3_2_margin_long_hold_mpc_${STAMP}.log"
if [[ -n "${STAGE3_2_RUN_DIR:-}" ]]; then RUN_DIR="$(stage32_abspath "${STAGE3_2_RUN_DIR}")"
else RUN_DIR="${PROJECT_DIR}/stage3_2_runs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms_${STAMP}"; fi
RESUME="${STAGE3_2_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage32_die "STAGE3_2_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_2_state.json" ]] || stage32_die "resume state missing: ${RUN_DIR}/stage3_2_state.json"
  stage32_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage32_die "fresh run directory is not empty: ${RUN_DIR}"
fi
stage32_detect_source_stage31
CONFIG="${STAGE3_2_CONFIG:-${PROJECT_DIR}/configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json}"
CONFIG="$(stage32_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage32_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE3_2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE3_2_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage3_2_$(id -u)}"
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE3_2_RUN_DIR="${RUN_DIR}" STAGE3_2_RESUME="${RESUME}" STAGE3_2_CONFIG="${CONFIG}" \
  STAGE3_2_COMMAND="${STAGE3_2_COMMAND:-all}" STAGE3_2_BACKEND="${STAGE3_2_BACKEND:-ray}" \
  SOURCE_STAGE3_1_RUN="${SOURCE_STAGE3_1_RUN}" SOURCE_STAGE3_0_RUN="${SOURCE_STAGE3_0_RUN:-}" SOURCE_STAGE2_2_RUN="${SOURCE_STAGE2_2_RUN:-}" \
  STAGE3_2_WORKERS="${STAGE3_2_WORKERS:-96}" STAGE3_2_TSC_WORKSPACE_ROOT="${WORKSPACE}" \
  STAGE3_2_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  bash "${PROJECT_DIR}/run_stage3_2_svd3_margin_long_hold_mpc_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage3_2_runs/stage3_2_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_2_margin_long_hold_mpc.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_2_margin_long_hold_mpc.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_2_runs/latest_stage3_2_run.txt"
echo "[Stage3.2] pid=${PID}"
echo "[Stage3.2] run_dir=${RUN_DIR}"
echo "[Stage3.2] log=${LOG_FILE}"
echo "[Stage3.2] follow: tail -f \"${LOG_FILE}\""
