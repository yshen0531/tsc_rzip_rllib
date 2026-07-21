#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
mkdir -p logs/nohup
STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG_FILE="${PROJECT_DIR}/logs/nohup/stage2_1_svd3_dual_archive_${STAMP}.log"
printf '%s\n' "${LOG_FILE}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.log"
nohup bash "${PROJECT_DIR}/run_stage2_1_svd3_dual_archive_native.sh" >"${LOG_FILE}" 2>&1 &
PID=$!
printf '%s\n' "${PID}" > "${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.pid"
echo "Stage2.1 started: pid=${PID}"
echo "Log: ${LOG_FILE}"
