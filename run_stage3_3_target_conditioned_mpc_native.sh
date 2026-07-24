#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_3_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_3_shell_common.sh"
stage33_project_init
stage33_find_python
stage33_runtime_env

CONFIG="${STAGE3_3_CONFIG:-${PROJECT_DIR}/configs/stage3_3_target_conditioned_receding_horizon_mpc_250ms.json}"
CONFIG="$(stage33_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage33_die "Stage3.3 config not found: ${CONFIG}"
COMMAND="${STAGE3_3_COMMAND:-all}"
case "${COMMAND}" in prepare|warmstart|refine-round|refine|library-confirm|calibrate|holdout|confirm|analyze|all) ;; *) stage33_die "invalid STAGE3_3_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE3_3_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage33_die "invalid STAGE3_3_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE3_3_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage33_die "STAGE3_3_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE3_3_RUN_DIR:-}" ]]; then RUN_DIR="$(stage33_abspath "${STAGE3_3_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage3_3_runs/stage3_3_target_conditioned_receding_horizon_mpc_250ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage3_3_runs/stage3_3_target_conditioned_receding_horizon_mpc_250ms_${STAMP}_${suffix}"; done
fi
export STAGE3_3_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage3_3_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_3_state.json" ]] || stage33_die "resume requested but state is missing: ${RUN_DIR}/stage3_3_state.json"
  stage33_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage33_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or STAGE3_3_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage33_detect_source_stage32
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_3_runs/latest_stage3_3_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage33_ray_stop
  stage33_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage33_ray_stop
stage33_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE3_3_TSC_RUN_ROOT}"

cat <<EOF
[Stage3.3] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage3.3] source_stage3_2_run=${SOURCE_STAGE3_2_RUN}
[Stage3.3] run_dir=${RUN_DIR}
[Stage3.3] config=${CONFIG}
[Stage3.3] command=${COMMAND}
[Stage3.3] backend=${BACKEND}
[Stage3.3] resume=${RESUME}
[Stage3.3] workers=${STAGE3_3_WORKERS}
[Stage3.3] python=${PYTHON_BIN}
[Stage3.3] RAY_TMPDIR=${RAY_TMPDIR}
[Stage3.3] TSC_WORKSPACE_ROOT=${STAGE3_3_TSC_WORKSPACE_ROOT}
[Stage3.3] TSC_RUN_ROOT=${STAGE3_3_TSC_RUN_ROOT}
[Stage3.3] Complete standalone tree: no Git, network, or external code tree is used.
[Stage3.3] Ray capacity is fixed at the configured campaign worker count for every variable-size wave.
[Stage3.3] Stage3.2 250 ms open-loop strict results and its 125x75 real-TSC Jacobian are reused.
[Stage3.3] Phase A/B build target-conditioned 250 ms nominal trajectories; Phase C confirms the library.
[Stage3.3] Refinement model uses dimensionless central/secant derivatives with a conservative Stage3.2 Jacobian prior; one weak target cannot abort the whole campaign.
[Stage3.3] Phase D/E resolve a bounded future-sequence problem every 10 ms and apply only the first correction.
[Stage3.3] Calibration chooses one global controller scale; held-out targets/disturbances are not used for scale selection.
[Stage3.3] R/Z hard gate remains 30 mm / 0.10 m/s; the 10 kA Ip safety gate is unchanged.
[Stage3.3] Ip tracking tolerances for the additional-heating setup: terminal <= 2000 A, hold RMS <= 2400 A, sustained max <= 4000 A.
[Stage3.3] Tested disturbances are not genuine new initial states, plant parameters, noise, or latency.
[Stage3.3] Final task remains robust causal control; residual RL is bounded and secondary.
[Stage3.3] SIGKILL cannot be intercepted; completed JSON.GZ results remain resumable.
EOF

ARGS=(--config "${CONFIG}" --source-stage3-2-run "${SOURCE_STAGE3_2_RUN}" --run-dir "${RUN_DIR}" --command "${COMMAND}" --backend "${BACKEND}")
if [[ "${RESUME}" != 1 ]]; then ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_3_target_conditioned_mpc.py" "${ARGS[@]}"
