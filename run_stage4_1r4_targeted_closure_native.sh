#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r4_shell_common.sh"
stage41r4_project_init
stage41r4_find_python
stage41r4_runtime_env
CONFIG="${STAGE4_1R4_CONFIG:-${PROJECT_DIR}/configs/stage4_1r4_targeted_closure_370ms.json}"
CONFIG="$(stage41r4_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r4_die "Stage4.1R4 config not found: ${CONFIG}"
COMMAND="${STAGE4_1R4_COMMAND:-all}"
case "${COMMAND}" in all|prepare|reclassify|weak_slew|estimator|restart|confirm|analyze) ;; *) stage41r4_die "invalid STAGE4_1R4_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE4_1R4_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41r4_die "invalid STAGE4_1R4_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1R4_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r4_die "STAGE4_1R4_RESUME must be 0 or 1" ;; esac
if [[ -n "${STAGE4_1R4_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r4_abspath "${STAGE4_1R4_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1r4_runs/stage4_1r4_targeted_closure_370ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix+1))
    RUN_DIR="${PROJECT_DIR}/stage4_1r4_runs/stage4_1r4_targeted_closure_370ms_${STAMP}_${suffix}"
  done
fi
export STAGE4_1R4_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1r4_runs" "${PROJECT_DIR}/logs/nohup"
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r4_state.json" ]] || stage41r4_die "resume state missing: ${RUN_DIR}/stage4_1r4_state.json"
  stage41r4_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage41r4_die "fresh run directory is not empty: ${RUN_DIR}"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage41r4_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r4_runs/latest_stage4_1r4_run.txt"
cleanup_on_exit() { local status=$?; trap - EXIT; set +e; stage41r4_ray_stop; stage41r4_cleanup_runtime; exit "${status}"; }
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41r4_ray_stop
stage41r4_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1R4_TSC_RUN_ROOT}"
cat <<EOF
[Stage4.1R4] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1R4] source_stage4_1r3_run=${SOURCE_STAGE4_1R3_RUN}
[Stage4.1R4] run_dir=${RUN_DIR}
[Stage4.1R4] config=${CONFIG}
[Stage4.1R4] command=${COMMAND}
[Stage4.1R4] backend=${BACKEND}
[Stage4.1R4] resume=${RESUME}
[Stage4.1R4] workers=${STAGE4_1R4_WORKERS}
[Stage4.1R4] python=${PYTHON_BIN}
[Stage4.1R4] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1R4] TSC_WORKSPACE_ROOT=${STAGE4_1R4_TSC_WORKSPACE_ROOT}
[Stage4.1R4] TSC_RUN_ROOT=${STAGE4_1R4_TSC_RUN_ROOT}
[Stage4.1R4] Stage4.1R3 regression/observer/recovery/noise/history/confirmation results are frozen and reused.
[Stage4.1R4] The gain-estimation category is reclassified correctly when no open-loop baseline passes exist.
[Stage4.1R4] The 0.9x-slew closure uses 370 ms, permits arrival by 270 ms, and requires 100 ms follow-up hold.
[Stage4.1R4] A finite online 0/1/2-step delay and 0.9/1.0/1.1 slew hypothesis bank is tested from measured coil-current increments.
[Stage4.1R4] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1R4] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF
ARGS=(--config "${CONFIG}" --source-stage4-1r3-run "${SOURCE_STAGE4_1R3_RUN}" --run-dir "${RUN_DIR}" --backend "${BACKEND}" --command "${COMMAND}")
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r4_targeted_closure.py" "${ARGS[@]}"
