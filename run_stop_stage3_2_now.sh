#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage3_2_shell_common.sh"
stage32_project_init; stage32_find_python
PID_FILE="${PROJECT_DIR}/stage3_2_runs/stage3_2_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(head -n1 "${PID_FILE}" | tr -dc '0-9')"
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    CMD="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
    if [[ "${CMD}" == *"stage3_2"* ]]; then
      PGID="$(ps -o pgid= -p "${PID}" 2>/dev/null | tr -d ' ' || true)"
      if [[ -n "${PGID}" ]]; then kill -TERM -- "-${PGID}" 2>/dev/null || true; sleep 3; kill -KILL -- "-${PGID}" 2>/dev/null || true
      else kill -TERM "${PID}" 2>/dev/null || true; fi
    else echo "[Stage3.2 stop] saved PID ${PID} is not Stage3.2; not killing it."; fi
  fi
  rm -f "${PID_FILE}"
fi
stage32_ray_stop; stage32_cleanup_runtime
echo "[Stage3.2 stop] process group, Ray, and /tmp runtime were cleaned. Saved stage3_2_runs results were not deleted."
