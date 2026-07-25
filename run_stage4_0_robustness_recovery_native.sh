#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_0_shell_common.sh"
stage40_project_init
stage40_find_python
stage40_runtime_env
CONFIG="${STAGE4_CONFIG:-${STAGE4_0_CONFIG:-${PROJECT_DIR}/configs/stage4_0_robustness_recovery_350ms.json}}"
CONFIG="$(stage40_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage40_die "Stage4.0 config not found: ${CONFIG}"
COMMAND="${STAGE4_COMMAND:-${STAGE4_0_COMMAND:-all}}"
case "${COMMAND}" in all|prepare|heldout|recovery|uncertainty|preconditioned|restart|confirmation|analyze) ;; *) stage40_die "invalid STAGE4_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE4_BACKEND:-${STAGE4_0_BACKEND:-ray}}"
case "${BACKEND}" in ray|serial) ;; *) stage40_die "invalid STAGE4_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_RESUME:-${STAGE4_0_RESUME:-0}}"
case "${RESUME}" in 0|1) ;; *) stage40_die "STAGE4_RESUME must be 0 or 1" ;; esac
if [[ -n "${STAGE4_RUN_DIR:-${STAGE4_0_RUN_DIR:-}}" ]]; then RUN_DIR="$(stage40_abspath "${STAGE4_RUN_DIR:-${STAGE4_0_RUN_DIR}}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_0_runs/stage4_0_robustness_recovery_350ms_${STAMP}"
  suffix=0; while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage4_0_runs/stage4_0_robustness_recovery_350ms_${STAMP}_${suffix}"; done
fi
export STAGE4_RUN_DIR="${RUN_DIR}"
export STAGE4_0_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_0_runs" "${PROJECT_DIR}/logs/nohup"
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_0_state.json" ]] || stage40_die "resume state missing: ${RUN_DIR}/stage4_0_state.json"
  stage40_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then stage40_die "fresh run directory is not empty: ${RUN_DIR}"; fi
  mkdir -p "${RUN_DIR}"
fi
stage40_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_0_runs/latest_stage4_0_run.txt"
cleanup_on_exit() { local status=$?; trap - EXIT; set +e; stage40_ray_stop; stage40_cleanup_runtime; exit "${status}"; }
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage40_ray_stop
stage40_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_TSC_RUN_ROOT}"
cat <<EOF
[Stage4.0] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.0] source_stage3_4_run=${SOURCE_STAGE3_4_RUN}
[Stage4.0] run_dir=${RUN_DIR}
[Stage4.0] config=${CONFIG}
[Stage4.0] command=${COMMAND}
[Stage4.0] backend=${BACKEND}
[Stage4.0] resume=${RESUME}
[Stage4.0] workers=${STAGE4_WORKERS}
[Stage4.0] python=${PYTHON_BIN}
[Stage4.0] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.0] TSC_WORKSPACE_ROOT=${STAGE4_TSC_WORKSPACE_ROOT}
[Stage4.0] TSC_RUN_ROOT=${STAGE4_TSC_RUN_ROOT}
[Stage4.0] Campaign capacity is fixed at the requested ${STAGE4_WORKERS} workers (default 192); no silent fallback is allowed.
[Stage4.0] Stage3.4 target library, selected MPC scale, 175x105 Jacobian, hard gate, and controller weights are frozen.
[Stage4.0] Phases: genuinely held-out targets; disturbance fail-to-pass recovery; sensor/latency/actuation uncertainty; preconditioned hidden-state histories; discoverable alternate restart folders; confirmation.
[Stage4.0] Alternate restart validation is conditional on folders actually present under the TSC simulation root or STAGE4_START_FOLDERS.
[Stage4.0] Finite-envelope success is not deployment qualification or full plant-parameter robustness.
[Stage4.0] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF
ARGS=(--config "${CONFIG}" --source-stage3-4-run "${SOURCE_STAGE3_4_RUN}" --run-dir "${RUN_DIR}" --backend "${BACKEND}" --command "${COMMAND}")
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_0_robustness_recovery.py" "${ARGS[@]}"
