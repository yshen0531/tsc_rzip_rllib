#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_0_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_0_shell_common.sh"
stage30_project_init
stage30_find_python
stage30_runtime_env

CONFIG="${STAGE3_0_CONFIG:-${PROJECT_DIR}/configs/stage3_0_svd3_tail_sqp_150ms.json}"
CONFIG="$(stage30_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage30_die "Stage3.0 config not found: ${CONFIG}"
COMMAND="${STAGE3_0_COMMAND:-all}"
case "${COMMAND}" in prepare|screen|round|optimize|identify|confirm|analyze|all) ;; *) stage30_die "invalid STAGE3_0_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE3_0_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage30_die "invalid STAGE3_0_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE3_0_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage30_die "STAGE3_0_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE3_0_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage30_abspath "${STAGE3_0_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix + 1))
    RUN_DIR="${PROJECT_DIR}/stage3_0_runs/stage3_0_svd3_tail_sqp_150ms_${STAMP}_${suffix}"
  done
fi
export STAGE3_0_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage3_0_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage3_0_state.json" ]] || stage30_die "resume requested but state is missing: ${RUN_DIR}/stage3_0_state.json"
  stage30_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage30_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or set STAGE3_0_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage30_detect_source_stage22
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_0_runs/latest_stage3_0_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage30_ray_stop
  stage30_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

stage30_ray_stop
stage30_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE3_TSC_RUN_ROOT}"

cat <<EOF
[Stage3.0] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage3.0] source_stage2_2_run=${SOURCE_STAGE2_2_RUN}
[Stage3.0] run_dir=${RUN_DIR}
[Stage3.0] config=${CONFIG}
[Stage3.0] command=${COMMAND}
[Stage3.0] backend=${BACKEND}
[Stage3.0] resume=${RESUME}
[Stage3.0] workers=${STAGE2_WORKERS}
[Stage3.0] python=${PYTHON_BIN}
[Stage3.0] RAY_TMPDIR=${RAY_TMPDIR}
[Stage3.0] TSC_WORKSPACE_ROOT=${STAGE3_TSC_WORKSPACE_ROOT}
[Stage3.0] TSC_RUN_ROOT=${STAGE3_TSC_RUN_ROOT}
[Stage3.0] Complete standalone source tree: no Git, network, or external base tree is used.
[Stage3.0] Arrival is allowed at 120, 130, 140, or 150 ms; 100 ms is not a hard deadline.
[Stage3.0] First nine actions are frozen from real-TSC Stage2.2 nominals; steps 9-14 are 18 independent tail variables.
[Stage3.0] Search = 96-tail screen + up to 3 rounds of 72 real-TSC finite differences and 24 SQP steps.
[Stage3.0] The exported MPC gain is an offline POC, not a validated online feedback controller.
[Stage3.0] Final task remains a robust feedback controller across initial states and targets.
[Stage3.0] SIGKILL cannot be intercepted. Completed candidate JSON files remain resumable.
EOF

ARGS=(
  "${COMMAND}"
  --config "${CONFIG}"
  --source-stage2-2-run "${SOURCE_STAGE2_2_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
)
if [[ "${RESUME}" != "1" ]]; then ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_0_tail_sqp.py" "${ARGS[@]}"
