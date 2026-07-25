#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r2_shell_common.sh"
stage41r2_project_init
stage41r2_find_python
PID_FILE="${PROJECT_DIR}/stage4_1r2_runs/stage4_1r2_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    CMD="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
    if [[ "${CMD}" == *stage4_1* ]]; then
      kill -TERM -- "-${PID}" 2>/dev/null || kill -TERM "${PID}" 2>/dev/null || true
      for _ in $(seq 1 30); do kill -0 "${PID}" 2>/dev/null || break; sleep 1; done
      kill -KILL -- "-${PID}" 2>/dev/null || kill -KILL "${PID}" 2>/dev/null || true
    fi
  fi
  rm -f "${PID_FILE}"
fi
stage41r2_ray_stop
stage41r2_cleanup_runtime
echo "[Stage4.1R2] stopped Ray and cleaned temporary runtime directories; saved run results were not deleted."
