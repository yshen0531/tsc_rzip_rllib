#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_1_shell_common.sh"
stage31_project_init
stage31_find_python
stage31_runtime_env

CONFIG="${STAGE3_1_CONFIG:-${PROJECT_DIR}/configs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms.json}"
CONFIG="$(stage31_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage31_die "Stage3.1 config not found: ${CONFIG}"
COMMAND="${STAGE3_1_COMMAND:-all}"
case "${COMMAND}" in prepare|round|optimize|identify|feedback|confirm|analyze|all) ;; *) stage31_die "invalid STAGE3_1_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE3_1_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage31_die "invalid STAGE3_1_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE3_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage31_die "STAGE3_1_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE3_1_RUN_DIR:-}" ]]; then RUN_DIR="$(stage31_abspath "${STAGE3_1_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage3_1_runs/stage3_1_svd3_adaptive_sqp_causal_mpc_150ms_${STAMP}_${suffix}"; done
fi
export STAGE3_1_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage3_1_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_1_state.json" ]] || stage31_die "resume requested but state is missing: ${RUN_DIR}/stage3_1_state.json"
  stage31_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage31_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or STAGE3_1_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage31_detect_source_stage30
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_1_runs/latest_stage3_1_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage31_ray_stop
  stage31_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage31_ray_stop
stage31_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE3_1_TSC_RUN_ROOT}"

cat <<EOF
[Stage3.1] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage3.1] source_stage3_0_run=${SOURCE_STAGE3_0_RUN}
[Stage3.1] run_dir=${RUN_DIR}
[Stage3.1] config=${CONFIG}
[Stage3.1] command=${COMMAND}
[Stage3.1] backend=${BACKEND}
[Stage3.1] resume=${RESUME}
[Stage3.1] workers=${STAGE3_1_WORKERS}
[Stage3.1] python=${PYTHON_BIN}
[Stage3.1] RAY_TMPDIR=${RAY_TMPDIR}
[Stage3.1] TSC_WORKSPACE_ROOT=${STAGE3_1_TSC_WORKSPACE_ROOT}
[Stage3.1] TSC_RUN_ROOT=${STAGE3_1_TSC_RUN_ROOT}
[Stage3.1] Complete standalone tree: no Git, network, or external code tree is used.
[Stage3.1] Stage3.0 screen is reused; it is not repeated.
[Stage3.1] Steps 0-7 are frozen; steps 8-14 are 21 independent three-mode variables.
[Stage3.1] Adaptive real-TSC trust regions expand/hold/shrink from measured agreement.
[Stage3.1] MPC features are dimensionless and use truncated-SVD/ridge regularization.
[Stage3.1] The 24-run causal feedback test is a limited POC, not robustness validation.
[Stage3.1] Final task remains robust causal feedback across initial states and targets.
[Stage3.1] SIGKILL cannot be intercepted; completed JSON.GZ results remain resumable.
EOF

ARGS=(--config "${CONFIG}" --source-stage3-0-run "${SOURCE_STAGE3_0_RUN}" --run-dir "${RUN_DIR}" --command "${COMMAND}" --backend "${BACKEND}")
if [[ "${RESUME}" != 1 ]]; then ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_1_adaptive_sqp_mpc.py" "${ARGS[@]}"
