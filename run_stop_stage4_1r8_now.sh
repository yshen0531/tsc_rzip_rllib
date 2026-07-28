#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_1r8_runs/stage4_1r8_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(tr -d '\r\n' < "${PID_FILE}")"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" || true
    sleep 2
    kill -9 "${PID}" 2>/dev/null || true
    echo "[Stage4.1R8 stop] stopped driver pid=${PID}"
  else
    echo "[Stage4.1R8 stop] recorded driver is not running: ${PID}"
  fi
  rm -f "${PID_FILE}"
else
  echo "[Stage4.1R8 stop] no driver pid file"
fi
if command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
pkill -f 'stage4_1r8_trusted_batch_calibration_queue_tail_closure.py' 2>/dev/null || true
