#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
export PROJECT_DIR
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

PYTHON_BIN="${PYTHON_BIN:-${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE2_1_CONFIG:-configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
SOURCE_STAGE1_1_RUN="${SOURCE_STAGE1_1_RUN:-}"
SOURCE_STAGE2_RUN="${SOURCE_STAGE2_RUN:-}"
export SOURCE_STAGE1_1_RUN SOURCE_STAGE2_RUN

if [[ -z "${SOURCE_STAGE1_1_RUN}" || ! -d "${SOURCE_STAGE1_1_RUN}" ]]; then
  echo "ERROR: export SOURCE_STAGE1_1_RUN=/absolute/path/to/completed_stage1_1_run" >&2
  exit 2
fi
if [[ -z "${SOURCE_STAGE2_RUN}" || ! -d "${SOURCE_STAGE2_RUN}" ]]; then
  echo "ERROR: export SOURCE_STAGE2_RUN=/absolute/path/to/completed_stage2_run" >&2
  exit 2
fi
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: Python interpreter not executable: ${PYTHON_BIN}" >&2
  exit 2
fi
if [[ ! -f "${CONFIG}" ]]; then
  echo "ERROR: Stage2.1 config not found: ${CONFIG}" >&2
  exit 2
fi

export STAGE2_WORKERS="${STAGE2_WORKERS:-192}"
export STAGE2_TSC_WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
export STAGE2_TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-${STAGE2_TSC_WORKSPACE_ROOT}/episode_runs}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_1_$(id -u)}"

mkdir -p "${STAGE2_TSC_WORKSPACE_ROOT}" "${STAGE2_TSC_RUN_ROOT}" "${RAY_TMPDIR}" stage2_1_runs logs/nohup
ulimit -n 1048576 2>/dev/null || true
ulimit -u 262144 2>/dev/null || true

cleanup_runtime() {
  set +e
  ray stop --force >/dev/null 2>&1 || true
  rm -rf "${RAY_TMPDIR}" 2>/dev/null || true
  mkdir -p "${STAGE2_TSC_WORKSPACE_ROOT}" "${STAGE2_TSC_RUN_ROOT}"
  find "${STAGE2_TSC_WORKSPACE_ROOT}" -mindepth 1 -maxdepth 1 \
    \( -name 'stage2_*' -o -name 'stage2_1_*' \) -exec rm -rf {} + 2>/dev/null || true
  find "${STAGE2_TSC_RUN_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
}
trap cleanup_runtime EXIT INT TERM

# A new Stage2.1 run is intentionally created every time this script is used.
cleanup_runtime
mkdir -p "${RAY_TMPDIR}" "${STAGE2_TSC_RUN_ROOT}"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
RUN_DIR="${STAGE2_1_RUN_DIR:-${PROJECT_DIR}/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_${STAMP}}"
mkdir -p "${RUN_DIR}"
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt"

cat <<EOF
[Stage2.1] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage2.1] source_stage1_1_run=${SOURCE_STAGE1_1_RUN}
[Stage2.1] source_stage2_run=${SOURCE_STAGE2_RUN}
[Stage2.1] run_dir=${RUN_DIR}
[Stage2.1] config=${CONFIG}
[Stage2.1] workers=${STAGE2_WORKERS}
[Stage2.1] RAY_TMPDIR=${RAY_TMPDIR}
[Stage2.1] TSC_WORKSPACE_ROOT=${STAGE2_TSC_WORKSPACE_ROOT}
[Stage2.1] TSC_RUN_ROOT=${STAGE2_TSC_RUN_ROOT}
[Stage2.1] 3 validated SVD modes x 5 nodes = 15 variables; search concentrates on the final 9.
[Stage2.1] The Stage2 30 mm hard gate is unchanged. Dual archives and smooth tube excess alter ranking only.
[Stage2.1] SIGKILL cannot be intercepted. Completed candidate JSON files remain resumable.
EOF

"${PYTHON_BIN}" -u scripts/stage2_1_trajectory_optimization.py all \
  --config "${CONFIG}" \
  --source-run "${SOURCE_STAGE1_1_RUN}" \
  --source-stage2-run "${SOURCE_STAGE2_RUN}" \
  --run-dir "${RUN_DIR}" \
  --backend ray \
  --no-resume
