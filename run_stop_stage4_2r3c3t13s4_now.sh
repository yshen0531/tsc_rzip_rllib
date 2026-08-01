#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_2r3c3t13s4_runs/stage4_2r3c3t13s4_driver.pid"
if [[ ! -f "${PID_FILE}" ]]; then
  printf '[T13S4] no pid file: %s\n' "${PID_FILE}"
  exit 0
fi
PID="$(tr -d '\r\n' < "${PID_FILE}")"
if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
  COMMAND="$(ps -p "${PID}" -o args= 2>/dev/null || true)"
  case "${COMMAND}" in
    *run_stage4_2r3c3t13s4_native.sh*|*stage4_2r3c3t13s4_lattice_transition_holdout.py*)
      kill -TERM "${PID}"
      printf '[T13S4] sent TERM to exact driver pid=%s\n' "${PID}"
      ;;
    *) echo "ERROR: pid is not the T13S4 driver; refusing to stop" >&2; exit 1 ;;
  esac
else
  printf '[T13S4] pid is not running: %s\n' "${PID}"
fi
