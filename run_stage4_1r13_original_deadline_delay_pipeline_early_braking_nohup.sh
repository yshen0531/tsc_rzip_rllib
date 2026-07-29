#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r13_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r13_shell_common.sh"
stage4_1r13_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_1R13_OUTPUT_ROOT}"
if [[ -z "${STAGE4_1R13_RUN_DIR:-}" ]]; then
  STAGE4_1R13_RUN_DIR="$(stage4_1r13_new_run_dir)"
  export STAGE4_1R13_RUN_DIR
fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r13_original_deadline_delay_pipeline_early_braking_${STAMP}.log"
PID_FILE="${STAGE4_1R13_OUTPUT_ROOT}/stage4_1r13_driver.pid"
LATEST_RUN_FILE="${STAGE4_1R13_OUTPUT_ROOT}/latest_stage4_1r13_run.txt"
LATEST_LOG_FILE="${PROJECT_DIR}/logs/nohup/latest_stage4_1r13_original_deadline_delay_pipeline_early_braking.log"
printf '%s\n' "${STAGE4_1R13_RUN_DIR}" > "${LATEST_RUN_FILE}"
printf '%s\n' "${LOG_FILE}" > "${LATEST_LOG_FILE}"
nohup env \
  STAGE4_1R13_PROJECT_DIR="${STAGE4_1R13_PROJECT_DIR}" \
  STAGE4_1R13_CONFIG="${STAGE4_1R13_CONFIG}" \
  STAGE4_1R13_PYTHON="${STAGE4_1R13_PYTHON}" \
  STAGE4_1R13_WORKERS="${STAGE4_1R13_WORKERS}" \
  STAGE4_1R13_BACKEND="${STAGE4_1R13_BACKEND}" \
  STAGE4_1R13_COMMAND="${STAGE4_1R13_COMMAND}" \
  STAGE4_1R13_RESUME="${STAGE4_1R13_RESUME}" \
  STAGE4_1R13_RUN_DIR="${STAGE4_1R13_RUN_DIR}" \
  STAGE4_1R13_SOURCE_STAGE4_1R12_RUN="${STAGE4_1R13_SOURCE_STAGE4_1R12_RUN:-}" \
  STAGE4_1R13_TSC_WORKSPACE_ROOT="${STAGE4_1R13_TSC_WORKSPACE_ROOT}" \
  STAGE4_1R13_TSC_RUN_ROOT="${STAGE4_1R13_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  "${PROJECT_DIR}/run_stage4_1r13_original_deadline_delay_pipeline_early_braking_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.1R13] pid=%s\n[Stage4.1R13] run_dir=%s\n[Stage4.1R13] log=%s\n' "${PID}" "${STAGE4_1R13_RUN_DIR}" "${LOG_FILE}"
