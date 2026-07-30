#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t1_shell_common.sh"
stage4_2r3c3t1_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_2R3C3T1_OUTPUT_ROOT}"
if [[ -z "${STAGE4_2R3C3T1_RUN_DIR:-}" ]]; then
  STAGE4_2R3C3T1_RUN_DIR="$(stage4_2r3c3t1_new_run_dir)"
  export STAGE4_2R3C3T1_RUN_DIR
fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t1_long_separation_zero_net_transport_identification_${STAMP}.log"
PID_FILE="${STAGE4_2R3C3T1_OUTPUT_ROOT}/stage4_2r3c3t1_driver.pid"
printf '%s\n' "${STAGE4_2R3C3T1_RUN_DIR}" \
  > "${STAGE4_2R3C3T1_OUTPUT_ROOT}/latest_stage4_2r3c3t1_run.txt"
printf '%s\n' "${LOG_FILE}" \
  > "${PROJECT_DIR}/logs/nohup/latest_stage4_2r3c3t1_long_separation_zero_net_transport_identification.log"
nohup env \
  STAGE4_2R3C3T1_PROJECT_DIR="${STAGE4_2R3C3T1_PROJECT_DIR}" \
  STAGE4_2R3C3T1_CONFIG="${STAGE4_2R3C3T1_CONFIG}" \
  STAGE4_2R3C3T1_PYTHON="${STAGE4_2R3C3T1_PYTHON}" \
  STAGE4_2R3C3T1_WORKERS="${STAGE4_2R3C3T1_WORKERS}" \
  STAGE4_2R3C3T1_BACKEND="${STAGE4_2R3C3T1_BACKEND}" \
  STAGE4_2R3C3T1_COMMAND="${STAGE4_2R3C3T1_COMMAND}" \
  STAGE4_2R3C3T1_RESUME="${STAGE4_2R3C3T1_RESUME}" \
  STAGE4_2R3C3T1_RUN_DIR="${STAGE4_2R3C3T1_RUN_DIR}" \
  STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T1_TSC_WORKSPACE_ROOT}" \
  STAGE4_2R3C3T1_TSC_RUN_ROOT="${STAGE4_2R3C3T1_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  "${PROJECT_DIR}/run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.2R3c3T1] pid=%s\n[Stage4.2R3c3T1] run_dir=%s\n[Stage4.2R3c3T1] log=%s\n' \
  "${PID}" "${STAGE4_2R3C3T1_RUN_DIR}" "${LOG_FILE}"
