#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3_shell_common.sh"
stage4_2r3_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_2R3_OUTPUT_ROOT}"
if [[ -z "${STAGE4_2R3_RUN_DIR:-}" ]]; then
  STAGE4_2R3_RUN_DIR="$(stage4_2r3_new_run_dir)"
  export STAGE4_2R3_RUN_DIR
fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_2r3_authentic_hidden_history_initial_state_${STAMP}.log"
PID_FILE="${STAGE4_2R3_OUTPUT_ROOT}/stage4_2r3_driver.pid"
printf '%s\n' "${STAGE4_2R3_RUN_DIR}" \
  > "${STAGE4_2R3_OUTPUT_ROOT}/latest_stage4_2r3_run.txt"
printf '%s\n' "${LOG_FILE}" \
  > "${PROJECT_DIR}/logs/nohup/latest_stage4_2r3_authentic_hidden_history_initial_state.log"
nohup env \
  STAGE4_2R3_PROJECT_DIR="${STAGE4_2R3_PROJECT_DIR}" \
  STAGE4_2R3_CONFIG="${STAGE4_2R3_CONFIG}" \
  STAGE4_2R3_PYTHON="${STAGE4_2R3_PYTHON}" \
  STAGE4_2R3_WORKERS="${STAGE4_2R3_WORKERS}" \
  STAGE4_2R3_BACKEND="${STAGE4_2R3_BACKEND}" \
  STAGE4_2R3_COMMAND="${STAGE4_2R3_COMMAND}" \
  STAGE4_2R3_RESUME="${STAGE4_2R3_RESUME}" \
  STAGE4_2R3_RUN_DIR="${STAGE4_2R3_RUN_DIR}" \
  STAGE4_2R3_SOURCE_STAGE4_2R2_RUN="${STAGE4_2R3_SOURCE_STAGE4_2R2_RUN:-}" \
  STAGE4_2R3_TSC_WORKSPACE_ROOT="${STAGE4_2R3_TSC_WORKSPACE_ROOT}" \
  STAGE4_2R3_TSC_RUN_ROOT="${STAGE4_2R3_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  "${PROJECT_DIR}/run_stage4_2r3_authentic_hidden_history_initial_state_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.2R3] pid=%s\n[Stage4.2R3] run_dir=%s\n[Stage4.2R3] log=%s\n' \
  "${PID}" "${STAGE4_2R3_RUN_DIR}" "${LOG_FILE}"
