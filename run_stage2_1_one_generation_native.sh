#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
export PROJECT_DIR
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export STAGE2_WORKERS="${STAGE2_WORKERS:-192}"
export STAGE2_TSC_WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
export STAGE2_TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${STAGE2_TSC_WORKSPACE_ROOT}/episode_runs}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"
PYTHON_BIN="${PYTHON_BIN:-${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE2_1_CONFIG:-configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
SOURCE_STAGE1_1_RUN="${SOURCE_STAGE1_1_RUN:-}"
SOURCE_STAGE2_RUN="${SOURCE_STAGE2_RUN:-}"
RUN_DIR="${STAGE2_1_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" && -f stage2_1_runs/latest_stage2_1_run.txt ]]; then
  RUN_DIR="$(cat stage2_1_runs/latest_stage2_1_run.txt)"
fi
if [[ -z "${RUN_DIR}" || ! -d "${RUN_DIR}" ]]; then
  echo "ERROR: set STAGE2_1_RUN_DIR to an existing Stage2.1 run" >&2; exit 2
fi
if [[ -z "${SOURCE_STAGE1_1_RUN}" || -z "${SOURCE_STAGE2_RUN}" ]]; then
  echo "ERROR: SOURCE_STAGE1_1_RUN and SOURCE_STAGE2_RUN are required" >&2; exit 2
fi
mkdir -p "${RAY_TMPDIR}" "${STAGE2_TSC_RUN_ROOT}"
trap 'ray stop --force >/dev/null 2>&1 || true; rm -rf "${RAY_TMPDIR}" 2>/dev/null || true' EXIT INT TERM
"${PYTHON_BIN}" -u scripts/stage2_1_trajectory_optimization.py generation \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN}" \
  --run-dir "${RUN_DIR}" \
  --backend ray
