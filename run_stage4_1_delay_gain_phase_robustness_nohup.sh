#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1_shell_common.sh"
stage41_project_init
stage41_find_python
command -v setsid >/dev/null 2>&1 || stage41_die "setsid is required"
mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage4_1_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1_delay_gain_phase_robustness_${STAMP}.log"
if [[ -n "${STAGE4_1_RUN_DIR:-}" ]]; then RUN_DIR="$(stage41_abspath "${STAGE4_1_RUN_DIR}")"; else RUN_DIR="${PROJECT_DIR}/stage4_1_runs/stage4_1_delay_gain_phase_robustness_350ms_${STAMP}"; fi
RESUME="${STAGE4_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41_die "STAGE4_1_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1_state.json" ]] || stage41_die "resume state missing: ${RUN_DIR}/stage4_1_state.json"
  stage41_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then stage41_die "fresh run directory is not empty: ${RUN_DIR}"; fi
stage41_detect_source
CONFIG="${STAGE4_1_CONFIG:-${PROJECT_DIR}/configs/stage4_1_delay_gain_phase_robustness_350ms.json}"
CONFIG="$(stage41_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41_die "config not found: ${CONFIG}"
WORKSPACE="${STAGE4_1_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE4_1_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_ROOT="${RAY_TMPDIR:-/tmp/stage4_1_$(id -u)}"
nohup setsid env PROJECT_DIR="${PROJECT_DIR}" TSC_ALL_ROOT="${TSC_ALL_ROOT}" PYTHON_BIN="${PYTHON_BIN}" \
  STAGE4_1_RUN_DIR="${RUN_DIR}" STAGE4_1_RESUME="${RESUME}" STAGE4_1_CONFIG="${CONFIG}" \
  STAGE4_1_COMMAND="${STAGE4_1_COMMAND:-all}" STAGE4_1_BACKEND="${STAGE4_1_BACKEND:-ray}" \
  SOURCE_STAGE4_0_RUN="${SOURCE_STAGE4_0_RUN}" STAGE4_1_WORKERS="${STAGE4_1_WORKERS:-${STAGE4_WORKERS:-128}}" \
  STAGE4_1_TSC_WORKSPACE_ROOT="${WORKSPACE}" STAGE4_1_TSC_RUN_ROOT="${RUN_ROOT}" RAY_TMPDIR="${RAY_ROOT}" \
  STAGE4_1_START_FOLDERS="${STAGE4_1_START_FOLDERS:-}" \
  "${PROJECT_DIR}/run_stage4_1_delay_gain_phase_robustness_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage4_1_runs/stage4_1_driver.pid"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1_runs/latest_stage4_1_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_1_delay_gain_phase_robustness.log"
echo "[Stage4.1] pid=${PID}"
echo "[Stage4.1] run_dir=${RUN_DIR}"
echo "[Stage4.1] log=${LOG_FILE}"
