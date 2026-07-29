#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r16_shell_common.sh"
stage4_1r16_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_1R16_OUTPUT_ROOT}"
if [[ -z "${STAGE4_1R16_RUN_DIR:-}" ]]; then STAGE4_1R16_RUN_DIR="$(stage4_1r16_new_run_dir)"; export STAGE4_1R16_RUN_DIR; fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r16_amplitude_certified_probe_derived_braking_closure_${STAMP}.log"
PID_FILE="${STAGE4_1R16_OUTPUT_ROOT}/stage4_1r16_driver.pid"
printf '%s\n' "${STAGE4_1R16_RUN_DIR}" > "${STAGE4_1R16_OUTPUT_ROOT}/latest_stage4_1r16_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_1r16_amplitude_certified_probe_derived_braking_closure.log"
nohup env \
  STAGE4_1R16_PROJECT_DIR="${STAGE4_1R16_PROJECT_DIR}" \
  STAGE4_1R16_CONFIG="${STAGE4_1R16_CONFIG}" \
  STAGE4_1R16_PYTHON="${STAGE4_1R16_PYTHON}" \
  STAGE4_1R16_WORKERS="${STAGE4_1R16_WORKERS}" \
  STAGE4_1R16_BACKEND="${STAGE4_1R16_BACKEND}" \
  STAGE4_1R16_COMMAND="${STAGE4_1R16_COMMAND}" \
  STAGE4_1R16_RESUME="${STAGE4_1R16_RESUME}" \
  STAGE4_1R16_RUN_DIR="${STAGE4_1R16_RUN_DIR}" \
  STAGE4_1R16_SOURCE_STAGE4_1R15B_RUN="${STAGE4_1R16_SOURCE_STAGE4_1R15B_RUN:-}" \
  STAGE4_1R16_TSC_WORKSPACE_ROOT="${STAGE4_1R16_TSC_WORKSPACE_ROOT}" \
  STAGE4_1R16_TSC_RUN_ROOT="${STAGE4_1R16_TSC_RUN_ROOT}" \
  RAY_TMPDIR="${RAY_TMPDIR}" \
  "${PROJECT_DIR}/run_stage4_1r16_amplitude_certified_probe_derived_braking_closure_native.sh" \
  >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.1R16] pid=%s\n[Stage4.1R16] run_dir=%s\n[Stage4.1R16] log=%s\n' "${PID}" "${STAGE4_1R16_RUN_DIR}" "${LOG_FILE}"
