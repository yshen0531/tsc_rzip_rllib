#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r5_shell_common.sh"
stage41r5_project_init
stage41r5_find_python
stage41r5_runtime_env

CONFIG="${STAGE4_1R5_CONFIG:-${PROJECT_DIR}/configs/stage4_1r5_adaptive_handover_closure_350ms.json}"
CONFIG="$(stage41r5_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r5_die "Stage4.1R5 config not found: ${CONFIG}"

COMMAND="${STAGE4_1R5_COMMAND:-all}"
case "${COMMAND}" in
  all|prepare|audit|estimator_only|handover|change_point|restart|confirm|analyze) ;;
  *) stage41r5_die "invalid STAGE4_1R5_COMMAND=${COMMAND}" ;;
esac
BACKEND="${STAGE4_1R5_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41r5_die "invalid STAGE4_1R5_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1R5_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r5_die "STAGE4_1R5_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE4_1R5_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r5_abspath "${STAGE4_1R5_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1r5_runs/stage4_1r5_adaptive_handover_closure_350ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix+1))
    RUN_DIR="${PROJECT_DIR}/stage4_1r5_runs/stage4_1r5_adaptive_handover_closure_350ms_${STAMP}_${suffix}"
  done
fi
export STAGE4_1R5_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1r5_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r5_state.json" ]] || stage41r5_die "resume state missing: ${RUN_DIR}/stage4_1r5_state.json"
  stage41r5_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage41r5_die "fresh run directory is not empty: ${RUN_DIR}"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage41r5_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r5_runs/latest_stage4_1r5_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage41r5_ray_stop
  stage41r5_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41r5_ray_stop
stage41r5_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1R5_TSC_RUN_ROOT}"

cat <<EOF
[Stage4.1R5] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1R5] source_stage4_1r4_run=${SOURCE_STAGE4_1R4_RUN}
[Stage4.1R5] run_dir=${RUN_DIR}
[Stage4.1R5] config=${CONFIG}
[Stage4.1R5] command=${COMMAND}
[Stage4.1R5] backend=${BACKEND}
[Stage4.1R5] resume=${RESUME}
[Stage4.1R5] workers=${STAGE4_1R5_WORKERS}
[Stage4.1R5] python=${PYTHON_BIN}
[Stage4.1R5] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1R5] TSC_WORKSPACE_ROOT=${STAGE4_1R5_TSC_WORKSPACE_ROOT}
[Stage4.1R5] TSC_RUN_ROOT=${STAGE4_1R5_TSC_RUN_ROOT}
[Stage4.1R5] Stage4.1R4 estimator accuracy and weak-slew closure are frozen; the failed abrupt adaptive-control handover is not treated as success.
[Stage4.1R5] Estimator accuracy is confirmed independently before controller handover is judged.
[Stage4.1R5] Static startup compares oracle, R4 abrupt unknown, R5 unknown bumpless, adjacent-prior bumpless, and persistent exact initialization.
[Stage4.1R5] Mid-episode delay/slew changes are finite diagnostic schedules, not a deployment actuator model.
[Stage4.1R5] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1R5] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF

ARGS=(
  --config "${CONFIG}"
  --source-stage4-1r4-run "${SOURCE_STAGE4_1R4_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
  --command "${COMMAND}"
)
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r5_adaptive_handover_closure.py" "${ARGS[@]}"
