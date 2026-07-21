#!/usr/bin/env bash
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-${SCRIPT_DIR}}"
cd "${PROJECT_DIR}" || exit 1

PID_FILE="${PROJECT_DIR}/stage2_1_runs/stage2_1_driver.pid"
ALT_PID_FILE="${PROJECT_DIR}/logs/nohup/latest_stage2_1_svd3_dual_archive.pid"
PID=""
for path in "${PID_FILE}" "${ALT_PID_FILE}"; do
  if [[ -f "${path}" ]]; then
    value="$(head -n 1 "${path}" 2>/dev/null | tr -d '[:space:]')"
    if [[ "${value}" =~ ^[0-9]+$ ]]; then PID="${value}"; break; fi
  fi
done

if [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null; then
  PROCESS_ARGS="$(ps -o args= -p "${PID}" 2>/dev/null || true)"
  case "${PROCESS_ARGS}" in
    *run_stage2_1_svd3_dual_archive_native.sh*|*scripts/stage2_1_trajectory_optimization.py*)
      PGID="$(ps -o pgid= -p "${PID}" 2>/dev/null | tr -d ' ' || true)"
      if [[ "${PGID}" =~ ^[0-9]+$ && "${PGID}" -gt 1 ]]; then
        kill -TERM -- "-${PGID}" 2>/dev/null || true
      else
        kill -TERM "${PID}" 2>/dev/null || true
      fi
      sleep 3
      if [[ "${PGID:-}" =~ ^[0-9]+$ && "${PGID}" -gt 1 ]]; then
        kill -KILL -- "-${PGID}" 2>/dev/null || true
      else
        kill -KILL "${PID}" 2>/dev/null || true
      fi
      ;;
    *)
      echo "WARNING: saved PID ${PID} no longer belongs to Stage2.1; refusing to signal it." >&2
      ;;
  esac
fi

pkill -TERM -f '[s]cripts/stage2_1_trajectory_optimization.py' 2>/dev/null || true
pkill -TERM -f '[r]un_stage2_1_svd3_dual_archive_native.sh' 2>/dev/null || true
sleep 2
pkill -KILL -f '[s]cripts/stage2_1_trajectory_optimization.py' 2>/dev/null || true
pkill -KILL -f '[r]un_stage2_1_svd3_dual_archive_native.sh' 2>/dev/null || true

TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
PYTHON_BIN="${PYTHON_BIN:-${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python}"
RAY_CLI="$(dirname "${PYTHON_BIN}")/ray"
if [[ -x "${RAY_CLI}" ]]; then
  "${RAY_CLI}" stop --force >/dev/null 2>&1 || true
elif command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi

WORKSPACE="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${WORKSPACE}/episode_runs}"
RAY_TMP="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"
for value in "${WORKSPACE}" "${RUN_ROOT}" "${RAY_TMP}"; do
  if [[ -z "${value}" || "${value}" != /tmp/* || "${value}" == "/tmp" || "${value}" == "/tmp/" ]]; then
    echo "WARNING: refusing to clean unsafe temporary path: ${value}" >&2
    exit 2
  fi
done
mkdir -p "${WORKSPACE}" "${RUN_ROOT}"
find "${WORKSPACE}" -mindepth 1 -maxdepth 1 -type d \
  \( -name 'stage2_*' -o -name 'stage2_1_*' \) -exec rm -rf -- {} + 2>/dev/null || true
find "${RUN_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
rm -rf -- "${RAY_TMP}" 2>/dev/null || true
rm -f -- "${PID_FILE}" "${ALT_PID_FILE}" 2>/dev/null || true

echo "[Stage2.1] driver/process group stopped; Ray and temporary /tmp runtime directories cleaned."
echo "[Stage2.1] result directories under stage2_1_runs were not deleted."
