#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_1r11_runs/stage4_1r11_driver.pid"
if [[ ! -f "${PID_FILE}" ]]; then
  echo "[Stage4.1R11 stop] no pid file: ${PID_FILE}"
  exit 0
fi
PID="$(tr -d '\r\n' < "${PID_FILE}")"
if [[ ! "${PID}" =~ ^[1-9][0-9]*$ ]]; then
  echo "ERROR: invalid pid in ${PID_FILE}: ${PID}" >&2
  exit 1
fi
if kill -0 "${PID}" 2>/dev/null; then
  kill -TERM "${PID}"
  echo "[Stage4.1R11 stop] sent SIGTERM to ${PID}"
else
  echo "[Stage4.1R11 stop] process ${PID} is not running"
fi
