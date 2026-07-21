#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_1_shell_common.sh"
stage21_project_init
stage21_find_python
command -v setsid >/dev/null 2>&1 || stage21_die "setsid is required for the nohup launcher"

mkdir -p "${PROJECT_DIR}/logs/nohup" "${PROJECT_DIR}/stage2_1_runs"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage2_1_svd3_dual_archive_${STAMP}.log"

if [[ -n "${STAGE2_1_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage21_abspath "${STAGE2_1_RUN_DIR}")"
else
  RUN_DIR="${PROJECT_DIR}/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_${STAMP}_${suffix}"
  done
fi

RESUME="${STAGE2_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage21_die "STAGE2_1_RESUME must be 0 or 1" ;; esac
if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage2_1_state.json" ]] || \
    stage21_die "resume requested but state is missing: ${RUN_DIR}/stage2_1_state.json"
  stage21_sources_from_existing_run "${RUN_DIR}"
elif [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  stage21_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE2_1_RESUME=1"
fi
stage21_detect_source_stage2
stage21_detect_source_stage1
CONFIG="${STAGE2_1_CONFIG:-${PROJECT_DIR}/configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
CONFIG="$(stage21_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage21_die "Stage2.1 config not found: ${CONFIG}"

WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${WORKSPACE_ROOT}/episode_runs}"
RAY_RUNTIME_ROOT="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"

# Pass validated, absolute paths through setsid. The native launcher validates
# them again before importing the optimization module.
nohup setsid env \
  PROJECT_DIR="${PROJECT_DIR}" \
  TSC_ALL_ROOT="${TSC_ALL_ROOT}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  STAGE2_1_RUN_DIR="${RUN_DIR}" \
  STAGE2_1_RESUME="${RESUME}" \
  STAGE2_1_CONFIG="${CONFIG}" \
  STAGE2_1_COMMAND="${STAGE2_1_COMMAND:-all}" \
  STAGE2_1_BACKEND="${STAGE2_1_BACKEND:-ray}" \
  SOURCE_STAGE1_1_RUN="${SOURCE_STAGE1_1_RUN:-}" \
  SOURCE_STAGE2_RUN="${SOURCE_STAGE2_RUN:-}" \
  STAGE2_1_WORKERS="${STAGE2_1_WORKERS:-${STAGE2_WORKERS:-192}}" \
  STAGE2_TSC_WORKSPACE_ROOT="${WORKSPACE_ROOT}" \
  STAGE2_TSC_RUN_ROOT="${TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_RUNTIME_ROOT}" \
  bash "${PROJECT_DIR}/run_stage2_1_svd3_dual_archive_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!

printf '%s\n' "${PID}" > "${PROJECT_DIR}/stage2_1_runs/stage2_1_driver.pid"
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.pid"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.log"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt"

echo "[Stage2.1] pid=${PID}"
echo "[Stage2.1] run_dir=${RUN_DIR}"
echo "[Stage2.1] log=${LOG_FILE}"
echo "[Stage2.1] follow: tail -f \"${LOG_FILE}\""
