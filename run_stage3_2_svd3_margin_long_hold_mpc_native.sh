#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_2_shell_common.sh"
stage32_project_init
stage32_find_python
stage32_runtime_env

CONFIG="${STAGE3_2_CONFIG:-${PROJECT_DIR}/configs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms.json}"
CONFIG="$(stage32_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage32_die "Stage3.2 config not found: ${CONFIG}"
COMMAND="${STAGE3_2_COMMAND:-all}"
case "${COMMAND}" in prepare|margin-round|margin|extension|hold-round|hold|identify|feedback|confirm|analyze|all) ;; *) stage32_die "invalid STAGE3_2_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE3_2_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage32_die "invalid STAGE3_2_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE3_2_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage32_die "STAGE3_2_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE3_2_RUN_DIR:-}" ]]; then RUN_DIR="$(stage32_abspath "${STAGE3_2_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage3_2_runs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage3_2_runs/stage3_2_svd3_margin_long_hold_causal_mpc_250ms_${STAMP}_${suffix}"; done
fi
export STAGE3_2_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage3_2_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_2_state.json" ]] || stage32_die "resume requested but state is missing: ${RUN_DIR}/stage3_2_state.json"
  stage32_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage32_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or STAGE3_2_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage32_detect_source_stage31
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_2_runs/latest_stage3_2_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage32_ray_stop
  stage32_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage32_ray_stop
stage32_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE3_2_TSC_RUN_ROOT}"

cat <<EOF
[Stage3.2] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage3.2] source_stage3_1_run=${SOURCE_STAGE3_1_RUN}
[Stage3.2] run_dir=${RUN_DIR}
[Stage3.2] config=${CONFIG}
[Stage3.2] command=${COMMAND}
[Stage3.2] backend=${BACKEND}
[Stage3.2] resume=${RESUME}
[Stage3.2] workers=${STAGE3_2_WORKERS}
[Stage3.2] ray_capacity_policy=configured campaign capacity; later waves cannot exceed the initialized cluster
[Stage3.2] ray_capacity_guard=undersized existing Ray clusters fail immediately; no silent slow fallback
[Stage3.2] python=${PYTHON_BIN}
[Stage3.2] RAY_TMPDIR=${RAY_TMPDIR}
[Stage3.2] TSC_WORKSPACE_ROOT=${STAGE3_2_TSC_WORKSPACE_ROOT}
[Stage3.2] TSC_RUN_ROOT=${STAGE3_2_TSC_RUN_ROOT}
[Stage3.2] Complete standalone tree: no Git, network, or external code tree is used.
[Stage3.2] Ray cluster capacity is fixed at the configured worker count; wave size cannot under-size later waves.
[Stage3.2] Stage3.1 confirmed strict candidates are reused; Stage3.1 optimization is not repeated.
[Stage3.2] Hard gate remains 30 mm / 0.10 m/s / 10 kA; arrival must complete by 150 ms and hold through 250 ms.
[Stage3.2] Phase A optimizes signed 150 ms margin; Phase B/C extend and optimize long hold; Phase D/E identify and test full-horizon causal feedback.
[Stage3.2] Feedback selection uses signed margins and preservation/recovery, not zero-clipped violations.
[Stage3.2] The tested feedback envelope is not initial-state, plant-parameter, noise, or delay robustness.
[Stage3.2] Final task remains a robust causal feedback controller; residual RL is not the primary controller.
[Stage3.2] SIGKILL cannot be intercepted; completed JSON.GZ results remain resumable.
EOF

ARGS=(--config "${CONFIG}" --source-stage3-1-run "${SOURCE_STAGE3_1_RUN}" --run-dir "${RUN_DIR}" --command "${COMMAND}" --backend "${BACKEND}")
if [[ "${RESUME}" != 1 ]]; then ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_2_margin_long_hold_mpc.py" "${ARGS[@]}"
