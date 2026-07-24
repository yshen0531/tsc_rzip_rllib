#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage3_4_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage3_4_shell_common.sh"
stage34_project_init
stage34_find_python
stage34_runtime_env

CONFIG="${STAGE3_4_CONFIG:-${PROJECT_DIR}/configs/stage3_4_late_arrival_continuation_mpc_350ms.json}"
CONFIG="$(stage34_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage34_die "Stage3.4 config not found: ${CONFIG}"
COMMAND="${STAGE3_4_COMMAND:-all}"
case "${COMMAND}" in prepare|continue|library-confirm|identify|calibrate|holdout|confirm|analyze|all) ;; *) stage34_die "invalid STAGE3_4_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE3_4_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage34_die "invalid STAGE3_4_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE3_4_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage34_die "STAGE3_4_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE3_4_RUN_DIR:-}" ]]; then RUN_DIR="$(stage34_abspath "${STAGE3_4_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage3_4_runs/stage3_4_late_arrival_continuation_mpc_350ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage3_4_runs/stage3_4_late_arrival_continuation_mpc_350ms_${STAMP}_${suffix}"; done
fi
export STAGE3_4_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage3_4_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage3_4_state.json" ]] || stage34_die "resume requested but state is missing: ${RUN_DIR}/stage3_4_state.json"
  stage34_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage34_die "fresh run directory is not empty: ${RUN_DIR}. Use a new path or STAGE3_4_RESUME=1"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage34_detect_source_stage33
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage3_4_runs/latest_stage3_4_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage34_ray_stop
  stage34_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage34_ray_stop
stage34_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE3_4_TSC_RUN_ROOT}"

cat <<EOF2
[Stage3.4] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage3.4] source_stage3_3_run=${SOURCE_STAGE3_3_RUN}
[Stage3.4] run_dir=${RUN_DIR}
[Stage3.4] config=${CONFIG}
[Stage3.4] command=${COMMAND}
[Stage3.4] backend=${BACKEND}
[Stage3.4] resume=${RESUME}
[Stage3.4] workers=${STAGE3_4_WORKERS}
[Stage3.4] python=${PYTHON_BIN}
[Stage3.4] RAY_TMPDIR=${RAY_TMPDIR}
[Stage3.4] TSC_WORKSPACE_ROOT=${STAGE3_4_TSC_WORKSPACE_ROOT}
[Stage3.4] TSC_RUN_ROOT=${STAGE3_4_TSC_RUN_ROOT}
[Stage3.4] Complete standalone tree: no Git, network, or external code tree is used.
[Stage3.4] Arrival may complete at 120-250 ms and must then hold through 350 ms; the latest arrival therefore has 100 ms of follow-up hold.
[Stage3.4] R/Z hard gate remains 30 mm / 0.10 m/s; the 10 kA Ip safety gate is unchanged.
[Stage3.4] Additional-heating Ip compatibility limits remain terminal 2000 A, hold RMS 2400 A, sustained max 4000 A.
[Stage3.4] Mandatory targets are built by ordered continuation milestones and up to five real-TSC reduced-space refinement rounds.
[Stage3.4] One physical 105-D control sequence is evaluated once and can be rescored for multiple targets through the global trajectory cache.
[Stage3.4] Only a confirmed complete target library unlocks the 175x105 real-TSC identification and per-step receding-horizon MPC POC.
[Stage3.4] Calibration selects one positive global feedback scale; held-out scenarios are never used for scale selection.
[Stage3.4] Tested targets/disturbances are not genuine new initial states, plant parameters, noise, or latency.
[Stage3.4] Final task remains robust causal control; residual RL is bounded and secondary.
[Stage3.4] SIGKILL cannot be intercepted; completed JSON.GZ results remain resumable.
EOF2

ARGS=(--config "${CONFIG}" --source-stage3-3-run "${SOURCE_STAGE3_3_RUN}" --run-dir "${RUN_DIR}" --command "${COMMAND}" --backend "${BACKEND}")
if [[ "${RESUME}" != 1 ]]; then ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage3_4_late_arrival_continuation_mpc.py" "${ARGS[@]}"
