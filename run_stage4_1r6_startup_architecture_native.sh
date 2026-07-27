#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r6_shell_common.sh"
stage41r6_project_init
stage41r6_find_python
stage41r6_runtime_env

CONFIG="${STAGE4_1R6_CONFIG:-${PROJECT_DIR}/configs/stage4_1r6_startup_architecture_closure_350ms.json}"
CONFIG="$(stage41r6_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r6_die "Stage4.1R6 config not found: ${CONFIG}"

COMMAND="${STAGE4_1R6_COMMAND:-all}"
case "${COMMAND}" in
  all|prepare|audit|estimator|startup|restart|confirm|analyze) ;;
  *) stage41r6_die "invalid STAGE4_1R6_COMMAND=${COMMAND}" ;;
esac
BACKEND="${STAGE4_1R6_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41r6_die "invalid STAGE4_1R6_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1R6_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r6_die "STAGE4_1R6_RESUME must be 0 or 1" ;; esac

if [[ -n "${STAGE4_1R6_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r6_abspath "${STAGE4_1R6_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1r6_runs/stage4_1r6_startup_architecture_closure_350ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix+1))
    RUN_DIR="${PROJECT_DIR}/stage4_1r6_runs/stage4_1r6_startup_architecture_closure_350ms_${STAMP}_${suffix}"
  done
fi
export STAGE4_1R6_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1r6_runs" "${PROJECT_DIR}/logs/nohup"

if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r6_state.json" ]] || stage41r6_die "resume state missing: ${RUN_DIR}/stage4_1r6_state.json"
  stage41r6_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage41r6_die "fresh run directory is not empty: ${RUN_DIR}"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage41r6_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r6_runs/latest_stage4_1r6_run.txt"

cleanup_on_exit() {
  local status=$?
  trap - EXIT
  set +e
  stage41r6_ray_stop
  stage41r6_cleanup_runtime
  exit "${status}"
}
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41r6_ray_stop
stage41r6_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1R6_TSC_RUN_ROOT}"

cat <<EOF
[Stage4.1R6] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1R6] source_stage4_1r5_run=${SOURCE_STAGE4_1R5_RUN}
[Stage4.1R6] run_dir=${RUN_DIR}
[Stage4.1R6] config=${CONFIG}
[Stage4.1R6] command=${COMMAND}
[Stage4.1R6] backend=${BACKEND}
[Stage4.1R6] resume=${RESUME}
[Stage4.1R6] workers=${STAGE4_1R6_WORKERS}
[Stage4.1R6] python=${PYTHON_BIN}
[Stage4.1R6] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1R6] TSC_WORKSPACE_ROOT=${STAGE4_1R6_TSC_WORKSPACE_ROOT}
[Stage4.1R6] TSC_RUN_ROOT=${STAGE4_1R6_TSC_RUN_ROOT}
[Stage4.1R6] R5 final delay/slew identification and exact persistent initialization are frozen; the failed fully-unknown handover is not treated as success.
[Stage4.1R6] Tied model scores cannot lock. A unique, confidence-gated best hypothesis must persist for consecutive observations.
[Stage4.1R6] The primary deployment path is previous-shot/pre-shot persistent initialization plus online monitoring.
[Stage4.1R6] Adjacent priors use a 14-coil physical-increment handover blend; a conservative common-prefix cold start remains diagnostic.
[Stage4.1R6] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1R6] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF

ARGS=(
  --config "${CONFIG}"
  --source-stage4-1r5-run "${SOURCE_STAGE4_1R5_RUN}"
  --run-dir "${RUN_DIR}"
  --backend "${BACKEND}"
  --command "${COMMAND}"
)
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r6_startup_architecture_closure.py" "${ARGS[@]}"
