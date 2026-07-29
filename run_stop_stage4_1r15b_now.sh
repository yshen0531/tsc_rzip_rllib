#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${PROJECT_DIR}/stage4_1r15b_runs/stage4_1r15b_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(tr -d '\r\n' < "${PID_FILE}")"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then kill -TERM "${PID}"; printf '[Stage4.1R15B] sent TERM to pid=%s\n' "${PID}"; else printf '[Stage4.1R15B] pid is not running: %s\n' "${PID}"; fi
else printf '[Stage4.1R15B] no pid file: %s\n' "${PID_FILE}"; fi
if command -v ray >/dev/null 2>&1; then ray stop --force >/dev/null 2>&1 || true; fi
