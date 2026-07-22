#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_0_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_0_shell_common.sh"
stage30_project_init
stage30_find_python
command -v setsid >/dev/null 2>&1 || stage30_die "setsid is required for the nohup launcher"

mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage3_0_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage3_0_svd3_tail_sqp_${STAMP}.log"
if [[ -n "${STAGE3_0_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage30_abspath "${STAGE3_0_RUN_DIR}")"
else
  RUN_DIR="${PROJECT_DIR}/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_${STAMP}_${suffix}"
  done
fi
RESUME="${STAGE3_0_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage30_die "STAGE3_0_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage3_0_state.json" ]] || stage30_die "resume requested but state is missing: ${RUN_DIR}/stage3_0_state.json"
  stage30_source_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage30_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE3_0_RESUME=1"
fi
stage30_detect_source_stage22
CONFIG="${STAGE3_0_CONFIG:-${PROJECT_DIR}/configs/stage3_0_svd3_tail_sqp_150ms.json}"
CONFIG="$(stage30_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage30_die "Stage3.0 config not found: ${CONFIG}"

WORKSPACE_ROOT="${STAGE3_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
TSC_RUN_ROOT="${STAGE3_TSC_RUN_ROOT:-${WORKSPACE_ROOT}/episode_runs}"
RAY_RUNTIME_ROOT="${RAY_TMPDIR:-/tmp/stage3_0_$(id -u)}"

nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" \
  TSC_ALL_ROOT="${TSC_ALL_ROOT}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  STAGE3_0_RUN_DIR="${RUN_DIR}" \
  STAGE3_0_RESUME="${RESUME}" \
  STAGE3_0_CONFIG="${CONFIG}" \
  STAGE3_0_COMMAND="${STAGE3_0_COMMAND:-all}" \
  STAGE3_0_BACKEND="${STAGE3_0_BACKEND:-ray}" \
  SOURCE_STAGE2_2_RUN="${SOURCE_STAGE2_2_RUN}" \
  STAGE3_0_WORKERS="${STAGE3_0_WORKERS:-96}" \
  STAGE3_TSC_WORKSPACE_ROOT="${WORKSPACE_ROOT}" \
  STAGE3_TSC_RUN_ROOT="${TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_RUNTIME_ROOT}" \
  bash "${PROJECT_DIR}/run_stage3_0_svd3_tail_sqp_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage3_0_runs/stage3_0_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_0_svd3_tail_sqp.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage3_0_svd3_tail_sqp.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_0_runs/latest_stage3_0_run.txt"
echo "[Stage3.0] pid=${PID}"
echo "[Stage3.0] run_dir=${RUN_DIR}"
echo "[Stage3.0] log=${LOG_FILE}"
echo "[Stage3.0] follow: tail -f \"${LOG_FILE}\""
