#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_2r3c3t13s24d1r4_runs/stage4_2r3c3t13s24d1r4_driver.pid"
[[ -f "${PID_FILE}" ]] || { echo "D1R4 PID file missing"; exit 1; }
PID="$(cat "${PID_FILE}")"
[[ "${PID}" =~ ^[0-9]+$ ]] || { echo "invalid D1R4 PID" >&2; exit 1; }
CMD="$(ps -p "${PID}" -o cmd= || true)"
[[ "${CMD}" == *stage4_2r3c3t13s24d1r4* ]] || { echo "PID is not the D1R4 driver" >&2; exit 1; }
kill -TERM "${PID}"
printf 'stopped D1R4 driver pid=%s\n' "${PID}"
