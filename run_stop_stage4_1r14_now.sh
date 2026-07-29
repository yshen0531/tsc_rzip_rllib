#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_ROOT="${STAGE4_1R14_OUTPUT_ROOT:-${PROJECT_DIR}/stage4_1r14_runs}"
PID_FILE="${OUTPUT_ROOT}/stage4_1r14_driver.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(tr -d '\r\n' < "${PID_FILE}")"
  if [[ "${PID}" =~ ^[0-9]+$ ]] && kill -0 "${PID}" 2>/dev/null; then
    kill "${PID}" || true
    for _ in $(seq 1 30); do
      kill -0 "${PID}" 2>/dev/null || break
      sleep 1
    done
    if kill -0 "${PID}" 2>/dev/null; then
      kill -KILL "${PID}" || true
    fi
  fi
  rm -f "${PID_FILE}"
fi
if command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R14] stop request completed.\n'
