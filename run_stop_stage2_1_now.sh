#!/usr/bin/env bash
set -u
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
PID_FILE="${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.pid"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [[ "${PID}" =~ ^[0-9]+$ ]]; then
    kill -TERM "${PID}" 2>/dev/null || true
    sleep 2
    kill -KILL "${PID}" 2>/dev/null || true
  fi
fi
pkill -TERM -f 'stage2_1_trajectory_optimization.py' 2>/dev/null || true
pkill -TERM -f 'run_stage2_1_svd3_dual_archive_native.sh' 2>/dev/null || true
sleep 2
pkill -KILL -f 'stage2_1_trajectory_optimization.py' 2>/dev/null || true
ray stop --force >/dev/null 2>&1 || true
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"
WORKSPACE="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
rm -rf "${RAY_TMPDIR}" 2>/dev/null || true
mkdir -p "${WORKSPACE}" "${RUN_ROOT}"
find "${WORKSPACE}" -mindepth 1 -maxdepth 1 \( -name 'stage2_*' -o -name 'stage2_1_*' \) -exec rm -rf {} + 2>/dev/null || true
find "${RUN_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
echo "Stage2.1, Ray, and temporary /tmp/tsc_workspace runtime directories were stopped/cleaned."
