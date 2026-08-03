#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
mkdir -p logs/nohup
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s23d1_bounded_schedule_search_${STAMP}.log"
PID_FILE="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s23d1_bounded_schedule_search_${STAMP}.pid"
nohup "${PROJECT_DIR}/run_stage4_2r3c3t13s23d1_offline.sh" >"${LOG}" 2>&1 &
PID=$!
printf '%s\n' "${PID}" >"${PID_FILE}"
printf 'PID=%s\nLOG=%s\nPID_FILE=%s\n' "${PID}" "${LOG}" "${PID_FILE}"
