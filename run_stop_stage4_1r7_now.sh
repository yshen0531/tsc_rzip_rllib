#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r7_shell_common.sh"
stage41r7_project_init
stage41r7_find_python
PID_FILE="${PROJECT_DIR}/stage4_1r7_runs/stage4_1r7_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ "${PID}" =~ ^[0-9]+$ ]]; then
    kill -TERM -- "-${PID}" 2>/dev/null || kill -TERM "${PID}" 2>/dev/null || true
    sleep 2
    kill -KILL -- "-${PID}" 2>/dev/null || kill -KILL "${PID}" 2>/dev/null || true
  fi
  rm -f "${PID_FILE}"
fi
pkill -f 'stage4_1r7_precontrol_calibration_queue_startup.py' 2>/dev/null || true
stage41r7_ray_stop
stage41r7_cleanup_runtime
echo "[Stage4.1R7] stopped and runtime workspace cleaned; saved run results were not removed."
