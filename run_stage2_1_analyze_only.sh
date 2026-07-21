#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
export PROJECT_DIR
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
PYTHON_BIN="${PYTHON_BIN:-${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE2_1_CONFIG:-configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
RUN_DIR="${STAGE2_1_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" && -f stage2_1_runs/latest_stage2_1_run.txt ]]; then RUN_DIR="$(cat stage2_1_runs/latest_stage2_1_run.txt)"; fi
if [[ -z "${RUN_DIR}" ]]; then echo "ERROR: set STAGE2_1_RUN_DIR" >&2; exit 2; fi
"${PYTHON_BIN}" -u scripts/stage2_1_trajectory_optimization.py analyze \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN:?SOURCE_STAGE1_1_RUN is required}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN:?SOURCE_STAGE2_RUN is required}" \
  --run-dir "${RUN_DIR}" \
  --backend serial
