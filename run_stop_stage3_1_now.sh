#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_1_shell_common.sh"
stage31_project_init; stage31_find_python
PID_FILE="${PROJECT_DIR}/stage3_1_runs/stage3_1_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(head -n1 "${PID_FILE}" | tr -dc '0-9')"
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    CMD="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
    if [[ "${CMD}" == *"stage3_1"* ]]; then
      PGID="$(ps -o pgid= -p "${PID}" 2>/dev/null | tr -d ' ' || true)"
      if [[ -n "${PGID}" ]]; then kill -TERM -- "-${PGID}" 2>/dev/null || true; sleep 3; kill -KILL -- "-${PGID}" 2>/dev/null || true
      else kill -TERM "${PID}" 2>/dev/null || true; fi
    else echo "[Stage3.1 stop] saved PID ${PID} is not Stage3.1; not killing it."; fi
  fi
  rm -f "${PID_FILE}"
fi
stage31_ray_stop; stage31_cleanup_runtime
echo "[Stage3.1 stop] process group, Ray, and /tmp runtime were cleaned. Saved stage3_1_runs results were not deleted."
