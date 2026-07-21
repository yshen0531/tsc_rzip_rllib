#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_2_shell_common.sh"
stage22_project_init
stage22_find_python
stage22_runtime_env

CONFIG="${STAGE2_2_CONFIG:-${PROJECT_DIR}/configs/stage2_2_svd3_corner_feasibility_100ms.json}"
CONFIG="$(stage22_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage22_die "Stage2.2 config not found: ${CONFIG}"

COMMAND="${STAGE2_2_COMMAND:-all}"
case "${COMMAND}" in prepare|generation|optimize|confirm|analyze|all) ;; *) stage22_die "invalid STAGE2_2_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE2_2_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage22_die "invalid STAGE2_2_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE2_2_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage22_die "STAGE2_2_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE2_2_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage22_abspath "${STAGE2_2_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage2_2_runs/stage2_2_svd3_corner_feasibility_100ms_${STAMP}_${suffix}"
  done
fi
export STAGE2_2_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage2_2_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage2_2_state.json" ]] || stage22_die "resume requested but state is missing: ${RUN_DIR}/stage2_2_state.json"
  stage22_sources_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage22_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE2_2_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi

stage22_detect_source_stage21
stage22_detect_derived_sources
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage22_ray_stop
  stage22_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

stage22_ray_stop
stage22_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE2_TSC_RUN_ROOT}"

cat <<EOF
[Stage2.2] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage2.2] source_stage1_1_run=${SOURCE_STAGE1_1_RUN}
[Stage2.2] source_stage2_run=${SOURCE_STAGE2_RUN}
[Stage2.2] source_stage2_1_run=${SOURCE_STAGE2_1_RUN}
[Stage2.2] run_dir=${RUN_DIR}
[Stage2.2] config=${CONFIG}
[Stage2.2] command=${COMMAND}
[Stage2.2] backend=${BACKEND}
[Stage2.2] resume=${RESUME}
[Stage2.2] workers=${STAGE2_WORKERS}
[Stage2.2] python=${PYTHON_BIN}
[Stage2.2] RAY_TMPDIR=${RAY_TMPDIR}
[Stage2.2] TSC_WORKSPACE_ROOT=${STAGE2_TSC_WORKSPACE_ROOT}
[Stage2.2] TSC_RUN_ROOT=${STAGE2_TSC_RUN_ROOT}
[Stage2.2] Complete standalone source tree: no Git, network, or external base tree is used.
[Stage2.2] Stage2 + Stage2.1 raw trajectories are recomputed into one deduplicated feasibility catalog.
[Stage2.2] 3 SVD modes x 5 nodes remain unchanged; 96 candidates x at most 6 local generations.
[Stage2.2] The 30 mm / 0.10 m/s / Ip hard gate is unchanged. Surrogates rank proposals only.
[Stage2.2] SIGKILL cannot be intercepted. Completed candidate JSON files remain resumable.
EOF

ARGS=(
  "${COMMAND}"
  --config "${CONFIG}"
  --source-run "${SOURCE_STAGE1_1_RUN}"
  --source-stage2-run "${SOURCE_STAGE2_RUN}"
  --source-stage2-1-run "${SOURCE_STAGE2_1_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
)
if [[ "${RESUME}" != "1" ]]; then ARGS+=(--no-resume); fi

"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_2_trajectory_optimization.py" "${ARGS[@]}"
