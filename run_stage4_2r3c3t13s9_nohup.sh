#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s9_shell_common.sh"
stage4_2r3c3t13s9_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_2R3C3T13S9_OUTPUT_ROOT}"
if [[ -z "${STAGE4_2R3C3T13S9_RUN_DIR:-}" ]]; then
  STAGE4_2R3C3T13S9_RUN_DIR="$(stage4_2r3c3t13s9_new_run_dir)"
  export STAGE4_2R3C3T13S9_RUN_DIR
fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s9_unified_postqueue_q1_identification_${STAMP}.log"
PID_FILE="${STAGE4_2R3C3T13S9_OUTPUT_ROOT}/stage4_2r3c3t13s9_driver.pid"
printf '%s\n' "${STAGE4_2R3C3T13S9_RUN_DIR}" > "${STAGE4_2R3C3T13S9_OUTPUT_ROOT}/latest_stage4_2r3c3t13s9_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_2r3c3t13s9_unified_postqueue_q1_identification.log"
nohup env \
  STAGE4_2R3C3T13S9_PROJECT_DIR="${STAGE4_2R3C3T13S9_PROJECT_DIR}" \
  STAGE4_2R3C3T13S9_CONFIG="${STAGE4_2R3C3T13S9_CONFIG}" \
  STAGE4_2R3C3T13S9_PYTHON="${STAGE4_2R3C3T13S9_PYTHON}" \
  STAGE4_2R3C3T13S9_WORKERS="${STAGE4_2R3C3T13S9_WORKERS}" \
  STAGE4_2R3C3T13S9_BACKEND="${STAGE4_2R3C3T13S9_BACKEND}" \
  STAGE4_2R3C3T13S9_COMMAND="${STAGE4_2R3C3T13S9_COMMAND}" \
  STAGE4_2R3C3T13S9_RESUME="${STAGE4_2R3C3T13S9_RESUME}" \
  STAGE4_2R3C3T13S9_RUN_DIR="${STAGE4_2R3C3T13S9_RUN_DIR}" \
  STAGE4_2R3C3T13S9_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S9_TSC_WORKSPACE_ROOT}" \
  STAGE4_2R3C3T13S9_TSC_RUN_ROOT="${STAGE4_2R3C3T13S9_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  bash "${PROJECT_DIR}/run_stage4_2r3c3t13s9_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[T13S9] pid=%s\n[T13S9] run_dir=%s\n[T13S9] log=%s\n' "${PID}" "${STAGE4_2R3C3T13S9_RUN_DIR}" "${LOG_FILE}"
