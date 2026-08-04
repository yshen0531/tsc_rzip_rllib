#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r6_runs/stage4_2r3c3t13s24d1r14r6_driver.pid"
[[ -f "${PID_FILE}" ]] || { echo "ERROR: R6 PID file missing" >&2; exit 1; }
PID="$(tr -d '[:space:]' < "${PID_FILE}")"
[[ "${PID}" =~ ^[0-9]+$ ]] || { echo "ERROR: invalid R6 PID" >&2; exit 1; }
if ! kill -0 "${PID}" 2>/dev/null; then echo "R6 process ${PID} is not running"; exit 0; fi
COMMAND="$(ps -p "${PID}" -o args=)"
[[ "${COMMAND}" == *"run_stage4_2r3c3t13s24d1r14r6_native.sh"* || "${COMMAND}" == *"stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py"* ]] || { echo "ERROR: PID is not the exact R6 driver" >&2; exit 1; }
kill -TERM "${PID}"
printf 'Sent TERM only to exact R6 driver PID %s\n' "${PID}"
