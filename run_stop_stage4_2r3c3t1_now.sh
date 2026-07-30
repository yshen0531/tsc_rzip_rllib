#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_2r3c3t1_runs/stage4_2r3c3t1_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(tr -d '\r\n' < "${PID_FILE}")"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    COMMAND="$(ps -p "${PID}" -o args= 2>/dev/null || true)"
    case "${COMMAND}" in
      *run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_native.sh*|\
      *stage4_2r3c3t1_long_separation_zero_net_transport_identification.py*)
        kill -TERM "${PID}"
        printf '[Stage4.2R3c3T1] sent TERM to exact driver pid=%s\n' "${PID}"
        ;;
      *)
        echo "ERROR: pid ${PID} is not the Stage4.2R3c3T1 driver; refusing to stop" >&2
        exit 1
        ;;
    esac
  else
    printf '[Stage4.2R3c3T1] pid is not running: %s\n' "${PID}"
  fi
else
  printf '[Stage4.2R3c3T1] no pid file: %s\n' "${PID_FILE}"
fi
