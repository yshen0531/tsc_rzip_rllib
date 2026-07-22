#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_0_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_0_shell_common.sh"
stage30_project_init
stage30_find_python
PID_FILE="${PROJECT_DIR}/stage3_0_runs/stage3_0_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(head -n 1 "${PID_FILE}" | tr -dc '0-9')"
  if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
    CMD="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
    if [[ "${CMD}" == *"stage3_0"* ]]; then
      PGID="$(ps -o pgid= -p "${PID}" 2>/dev/null | tr -d ' ' || true)"
      if [[ -n "${PGID}" ]]; then
        kill -TERM -- "-${PGID}" 2>/dev/null || true
        sleep 3
        kill -KILL -- "-${PGID}" 2>/dev/null || true
      else
        kill -TERM "${PID}" 2>/dev/null || true
      fi
    else
      echo "[Stage3.0 stop] saved PID ${PID} no longer belongs to Stage3.0; not killing it."
    fi
  fi
  rm -f "${PID_FILE}"
fi
stage30_ray_stop
stage30_cleanup_runtime
echo "[Stage3.0 stop] Stage3.0 process group, Ray, and /tmp runtime workspaces were cleaned. Saved stage3_0_runs results were not deleted."
