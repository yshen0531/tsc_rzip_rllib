#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_2_shell_common.sh"
stage22_project_init
stage22_find_python
command -v setsid >/dev/null 2>&1 || stage22_die "setsid is required for the nohup launcher"

mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage2_2_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage2_2_svd3_corner_${STAMP}.log"

if [[ -n "${STAGE2_2_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage22_abspath "${STAGE2_2_RUN_DIR}")"
else
  RUN_DIR="${PROJECT_DIR}/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_${STAMP}_${suffix}"
  done
fi
RESUME="${STAGE2_2_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage22_die "STAGE2_2_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage2_2_state.json" ]] || stage22_die "resume requested but state is missing: ${RUN_DIR}/stage2_2_state.json"
  stage22_sources_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage22_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE2_2_RESUME=1"
fi
stage22_detect_source_stage21
stage22_detect_derived_sources
CONFIG="${STAGE2_2_CONFIG:-${PROJECT_DIR}/configs/stage2_2_svd3_corner_feasibility_100ms.json}"
CONFIG="$(stage22_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage22_die "Stage2.2 config not found: ${CONFIG}"

WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${WORKSPACE_ROOT}/episode_runs}"
RAY_RUNTIME_ROOT="${RAY_TMPDIR:-/tmp/stage2_2_$(id -u)}"

nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" \
  TSC_ALL_ROOT="${TSC_ALL_ROOT}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  STAGE2_2_RUN_DIR="${RUN_DIR}" \
  STAGE2_2_RESUME="${RESUME}" \
  STAGE2_2_CONFIG="${CONFIG}" \
  STAGE2_2_COMMAND="${STAGE2_2_COMMAND:-all}" \
  STAGE2_2_BACKEND="${STAGE2_2_BACKEND:-ray}" \
  SOURCE_STAGE1_1_RUN="${SOURCE_STAGE1_1_RUN}" \
  SOURCE_STAGE2_RUN="${SOURCE_STAGE2_RUN}" \
  SOURCE_STAGE2_1_RUN="${SOURCE_STAGE2_1_RUN}" \
  STAGE2_2_WORKERS="${STAGE2_2_WORKERS:-${STAGE2_WORKERS:-96}}" \
  STAGE2_TSC_WORKSPACE_ROOT="${WORKSPACE_ROOT}" \
  STAGE2_TSC_RUN_ROOT="${TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_RUNTIME_ROOT}" \
  bash "${PROJECT_DIR}/run_stage2_2_svd3_corner_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!

printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage2_2_runs/stage2_2_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_2_svd3_corner.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_2_svd3_corner.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt"

echo "[Stage2.2] pid=${PID}"
echo "[Stage2.2] run_dir=${RUN_DIR}"
echo "[Stage2.2] log=${LOG_FILE}"
echo "[Stage2.2] follow: tail -f \"${LOG_FILE}\""
