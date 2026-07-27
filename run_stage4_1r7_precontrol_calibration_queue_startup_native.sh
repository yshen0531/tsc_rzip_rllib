#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r7_shell_common.sh"
stage41r7_project_init
stage41r7_find_python
stage41r7_runtime_env

CONFIG="${STAGE4_1R7_CONFIG:-${PROJECT_DIR}/configs/stage4_1r7_precontrol_calibration_queue_startup_370ms.json}"
CONFIG="$(stage41r7_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r7_die "Stage4.1R7 config not found: ${CONFIG}"

COMMAND="${STAGE4_1R7_COMMAND:-all}"
case "${COMMAND}" in
  all|prepare|audit|calibrate|startup|restart|confirm|analyze) ;;
  *) stage41r7_die "invalid STAGE4_1R7_COMMAND=${COMMAND}" ;;
esac
BACKEND="${STAGE4_1R7_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41r7_die "invalid STAGE4_1R7_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1R7_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r7_die "STAGE4_1R7_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE4_1R7_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r7_abspath "${STAGE4_1R7_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1r7_runs/stage4_1r7_precontrol_calibration_queue_startup_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix+1))
    RUN_DIR="${PROJECT_DIR}/stage4_1r7_runs/stage4_1r7_precontrol_calibration_queue_startup_${STAMP}_${suffix}"
  done
fi
export STAGE4_1R7_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1r7_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r7_state.json" ]] || stage41r7_die "resume state missing: ${RUN_DIR}/stage4_1r7_state.json"
  stage41r7_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage41r7_die "fresh run directory is not empty: ${RUN_DIR}"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage41r7_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r7_runs/latest_stage4_1r7_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage41r7_ray_stop
  stage41r7_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41r7_ray_stop
stage41r7_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1R7_TSC_RUN_ROOT}"

cat <<EOF
[Stage4.1R7] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1R7] source_stage4_1r6_run=${SOURCE_STAGE4_1R6_RUN}
[Stage4.1R7] run_dir=${RUN_DIR}
[Stage4.1R7] config=${CONFIG}
[Stage4.1R7] command=${COMMAND}
[Stage4.1R7] backend=${BACKEND}
[Stage4.1R7] resume=${RESUME}
[Stage4.1R7] workers=${STAGE4_1R7_WORKERS}
[Stage4.1R7] python=${PYTHON_BIN}
[Stage4.1R7] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1R7] TSC_WORKSPACE_ROOT=${STAGE4_1R7_TSC_WORKSPACE_ROOT}
[Stage4.1R7] TSC_RUN_ROOT=${STAGE4_1R7_TSC_RUN_ROOT}
[Stage4.1R7] R6 finite-bank estimation and exact persistent startup are frozen; failed physical-blend/cold-start paths are not reused as success.
[Stage4.1R7] A separate bounded zero-net calibration episode identifies delay/slew, then TSC is reset before the main control trajectory.
[Stage4.1R7] The main action queue is primed consistently from the calibrated model before the first control action; primary startup uses no online handover.
[Stage4.1R7] The weak 0.9x-slew cases retain the validated 370 ms / 270 ms-arrival closure and no-anti-windup configuration.
[Stage4.1R7 R7a] Null-safe summaries, exact monitor matching, and phase-coverage guards are active; control law and experiment IDs are unchanged.
[Stage4.1R7] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1R7] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF

ARGS=(
  --config "${CONFIG}"
  --source-stage4-1r6-run "${SOURCE_STAGE4_1R6_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
  --command "${COMMAND}"
)
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r7_precontrol_calibration_queue_startup.py" "${ARGS[@]}"
