#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_4_shell_common.sh"
stage34_project_init
stage34_find_python
PID_FILE="${PROJECT_DIR}/stage3_4_runs/stage3_4_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    CMD="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
    if [[ "${CMD}" == *stage3_4* ]]; then
      kill -TERM -- "-${PID}" 2>/dev/null || kill -TERM "${PID}" 2>/dev/null || true
      for _ in $(seq 1 30); do kill -0 "${PID}" 2>/dev/null || break; sleep 1; done
      kill -KILL -- "-${PID}" 2>/dev/null || kill -KILL "${PID}" 2>/dev/null || true
    else
      echo "[Stage3.4 stop] PID ${PID} no longer belongs to Stage3.4; not killing it." >&2
    fi
  fi
  rm -f "${PID_FILE}"
fi
stage34_ray_stop
stage34_cleanup_runtime
echo "[Stage3.4 stop] Stage3.4/Ray stopped and /tmp runtime cleaned. Saved stage3_4_runs results were not deleted."
