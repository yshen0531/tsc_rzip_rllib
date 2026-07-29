#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r15b_shell_common.sh"
stage4_1r15b_validate_common
mkdir -p "${PROJECT_DIR}/logs/nohup" "${STAGE4_1R15B_OUTPUT_ROOT}"
if [[ -z "${STAGE4_1R15B_RUN_DIR:-}" ]]; then STAGE4_1R15B_RUN_DIR="$(stage4_1r15b_new_run_dir)"; export STAGE4_1R15B_RUN_DIR; fi
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_${STAMP}.log"
PID_FILE="${STAGE4_1R15B_OUTPUT_ROOT}/stage4_1r15b_driver.pid"
printf '%s\n' "${STAGE4_1R15B_RUN_DIR}" > "${STAGE4_1R15B_OUTPUT_ROOT}/latest_stage4_1r15b_run.txt"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation.log"
nohup env STAGE4_1R15B_PROJECT_DIR="${STAGE4_1R15B_PROJECT_DIR}" STAGE4_1R15B_CONFIG="${STAGE4_1R15B_CONFIG}" STAGE4_1R15B_PYTHON="${STAGE4_1R15B_PYTHON}" STAGE4_1R15B_WORKERS="${STAGE4_1R15B_WORKERS}" STAGE4_1R15B_BACKEND="${STAGE4_1R15B_BACKEND}" STAGE4_1R15B_COMMAND="${STAGE4_1R15B_COMMAND}" STAGE4_1R15B_RESUME="${STAGE4_1R15B_RESUME}" STAGE4_1R15B_RUN_DIR="${STAGE4_1R15B_RUN_DIR}" STAGE4_1R15B_SOURCE_STAGE4_1R15_RUN="${STAGE4_1R15B_SOURCE_STAGE4_1R15_RUN:-}" STAGE4_1R15B_TSC_WORKSPACE_ROOT="${STAGE4_1R15B_TSC_WORKSPACE_ROOT}" STAGE4_1R15B_TSC_RUN_ROOT="${STAGE4_1R15B_TSC_RUN_ROOT}" RAY_TMPDIR="${RAY_TMPDIR}" "${PROJECT_DIR}/run_stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_native.sh" >"${LOG_FILE}" 2>&1 < /dev/null &
PID=$!
printf '%s\n' "${PID}" > "${PID_FILE}"
printf '[Stage4.1R15B] pid=%s\n[Stage4.1R15B] run_dir=%s\n[Stage4.1R15B] log=%s\n' "${PID}" "${STAGE4_1R15B_RUN_DIR}" "${LOG_FILE}"
