#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_1_shell_common.sh"
stage21_project_init
stage21_find_python
stage21_runtime_env

CONFIG="${STAGE2_1_CONFIG:-${PROJECT_DIR}/configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json}"
CONFIG="$(stage21_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage21_die "Stage2.1 config not found: ${CONFIG}"

COMMAND="${STAGE2_1_COMMAND:-all}"
case "${COMMAND}" in
  prepare|generation|optimize|confirm|analyze|all) ;;
  *) stage21_die "invalid STAGE2_1_COMMAND=${COMMAND}" ;;
esac
BACKEND="${STAGE2_1_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage21_die "invalid STAGE2_1_BACKEND=${BACKEND}" ;; esac

RESUME="${STAGE2_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage21_die "STAGE2_1_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE2_1_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage21_abspath "${STAGE2_1_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage2_1_runs/stage2_1_svd3_dual_archive_tail_cem_100ms_${STAMP}_${suffix}"
  done
fi
export STAGE2_1_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage2_1_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage2_1_state.json" ]] || \
    stage21_die "resume requested but state is missing: ${RUN_DIR}/stage2_1_state.json"
  stage21_sources_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage21_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE2_1_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi

stage21_detect_source_stage2
stage21_detect_source_stage1
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage21_ray_stop
  stage21_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Stage2/Stage2.1 are not designed to share one local Ray runtime concurrently.
stage21_ray_stop
stage21_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE2_TSC_RUN_ROOT}"

cat <<EOF
[Stage2.1] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage2.1] source_stage1_1_run=${SOURCE_STAGE1_1_RUN}
[Stage2.1] source_stage2_run=${SOURCE_STAGE2_RUN}
[Stage2.1] run_dir=${RUN_DIR}
[Stage2.1] config=${CONFIG}
[Stage2.1] command=${COMMAND}
[Stage2.1] backend=${BACKEND}
[Stage2.1] resume=${RESUME}
[Stage2.1] workers=${STAGE2_WORKERS}
[Stage2.1] python=${PYTHON_BIN}
[Stage2.1] RAY_TMPDIR=${RAY_TMPDIR}
[Stage2.1] TSC_WORKSPACE_ROOT=${STAGE2_TSC_WORKSPACE_ROOT}
[Stage2.1] TSC_RUN_ROOT=${STAGE2_TSC_RUN_ROOT}
[Stage2.1] Complete standalone source tree: no Git, network, or external base tree is used.
[Stage2.1] 3 validated SVD modes x 5 nodes = 15 variables; search concentrates on the final 9.
[Stage2.1] The Stage2 30 mm hard gate is unchanged. Dual archives and smooth tube excess alter ranking only.
[Stage2.1] SIGKILL cannot be intercepted. Completed candidate JSON files remain resumable.
EOF

ARGS=(
  "${COMMAND}"
  --config "${CONFIG}"
  --source-run "${SOURCE_STAGE1_1_RUN}"
  --source-stage2-run "${SOURCE_STAGE2_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
)
if [[ "${RESUME}" != "1" ]]; then
  ARGS+=(--no-resume)
fi

"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage2_1_trajectory_optimization.py" "${ARGS[@]}"
