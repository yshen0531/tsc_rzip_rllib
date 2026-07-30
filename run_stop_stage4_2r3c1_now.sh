#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_2r3c1_runs/stage4_2r3c1_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(tr -d '\r\n' < "${PID_FILE}")"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    COMMAND="$(ps -p "${PID}" -o args= 2>/dev/null || true)"
    case "${COMMAND}" in
      *run_stage4_2r3c1_authenticated_visible_manifold_phase_mpc_native.sh*|\
      *stage4_2r3c1_authenticated_visible_manifold_phase_mpc.py*)
        kill -TERM "${PID}"
        printf '[Stage4.2R3c1] sent TERM to exact driver pid=%s\n' "${PID}"
        ;;
      *)
        echo "ERROR: pid ${PID} is not the Stage4.2R3c1 driver; refusing to stop" >&2
        exit 1
        ;;
    esac
  else
    printf '[Stage4.2R3c1] pid is not running: %s\n' "${PID}"
  fi
else
  printf '[Stage4.2R3c1] no pid file: %s\n' "${PID_FILE}"
fi
