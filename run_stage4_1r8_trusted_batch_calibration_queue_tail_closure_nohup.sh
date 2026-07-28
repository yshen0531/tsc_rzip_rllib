#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r8_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r8_shell_common.sh"
stage4_1r8_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_1R8_OUTPUT_ROOT}"
if [[ -z "${STAGE4_1R8_RUN_DIR:-}" ]]; then
  STAGE4_1R8_RUN_DIR="$(stage4_1r8_new_run_dir)"
  export STAGE4_1R8_RUN_DIR
fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r8_trusted_batch_calibration_queue_tail_closure_${STAMP}.log"
PID_FILE="${STAGE4_1R8_OUTPUT_ROOT}/stage4_1r8_driver.pid"
LATEST_RUN_FILE="${STAGE4_1R8_OUTPUT_ROOT}/latest_stage4_1r8_run.txt"
LATEST_LOG_FILE="${PROJECT_DIR}/logs/nohup/latest_stage4_1r8_trusted_batch_calibration_queue_tail_closure.log"
printf '%s\n' "${STAGE4_1R8_RUN_DIR}" > "${LATEST_RUN_FILE}"
printf '%s\n' "${LOG_FILE}" > "${LATEST_LOG_FILE}"
nohup env \
  STAGE4_1R8_PROJECT_DIR="${STAGE4_1R8_PROJECT_DIR}" \
  STAGE4_1R8_CONFIG="${STAGE4_1R8_CONFIG}" \
  STAGE4_1R8_PYTHON="${STAGE4_1R8_PYTHON}" \
  STAGE4_1R8_WORKERS="${STAGE4_1R8_WORKERS}" \
  STAGE4_1R8_BACKEND="${STAGE4_1R8_BACKEND}" \
  STAGE4_1R8_COMMAND="${STAGE4_1R8_COMMAND}" \
  STAGE4_1R8_RESUME="${STAGE4_1R8_RESUME}" \
  STAGE4_1R8_RUN_DIR="${STAGE4_1R8_RUN_DIR}" \
  STAGE4_1R8_SOURCE_STAGE4_1R7_RUN="${STAGE4_1R8_SOURCE_STAGE4_1R7_RUN:-}" \
  STAGE4_1R8_TSC_WORKSPACE_ROOT="${STAGE4_1R8_TSC_WORKSPACE_ROOT}" \
  STAGE4_1R8_TSC_RUN_ROOT="${STAGE4_1R8_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  "${PROJECT_DIR}/run_stage4_1r8_trusted_batch_calibration_queue_tail_closure_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.1R8] pid=%s\n[Stage4.1R8] run_dir=%s\n[Stage4.1R8] log=%s\n' "${PID}" "${STAGE4_1R8_RUN_DIR}" "${LOG_FILE}"
