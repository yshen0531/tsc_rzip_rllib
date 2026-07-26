#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r3_shell_common.sh"
stage41r3_project_init
stage41r3_find_python
stage41r3_runtime_env
CONFIG="${STAGE4_1R3_CONFIG:-${PROJECT_DIR}/configs/stage4_1r3_control_aware_residual_observer_350ms.json}"
CONFIG="$(stage41r3_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41r3_die "Stage4.1R3 config not found: ${CONFIG}"
COMMAND="${STAGE4_1R3_COMMAND:-all}"
case "${COMMAND}" in all|prepare|regression|ablation|recovery|structured|noise|history|restart|confirm|analyze) ;; *) stage41r3_die "invalid STAGE4_1R3_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE4_1R3_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41r3_die "invalid STAGE4_1R3_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1R3_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41r3_die "STAGE4_1R3_RESUME must be 0 or 1" ;; esac
if [[ -n "${STAGE4_1R3_RUN_DIR:-}" ]]; then
  RUN_DIR="$(stage41r3_abspath "${STAGE4_1R3_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1r3_runs/stage4_1r3_control_aware_residual_observer_350ms_${STAMP}"
  suffix=0
  while [[ -e "${RUN_DIR}" ]]; do
    suffix=$((suffix+1))
    RUN_DIR="${PROJECT_DIR}/stage4_1r3_runs/stage4_1r3_control_aware_residual_observer_350ms_${STAMP}_${suffix}"
  done
fi
export STAGE4_1R3_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1r3_runs" "${PROJECT_DIR}/logs/nohup"
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r3_state.json" ]] || stage41r3_die "resume state missing: ${RUN_DIR}/stage4_1r3_state.json"
  stage41r3_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    stage41r3_die "fresh run directory is not empty: ${RUN_DIR}"
  fi
  mkdir -p "${RUN_DIR}"
fi
stage41r3_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1r3_runs/latest_stage4_1r3_run.txt"
cleanup_on_exit() { local status=$?; trap - EXIT; set +e; stage41r3_ray_stop; stage41r3_cleanup_runtime; exit "${status}"; }
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41r3_ray_stop
stage41r3_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1R3_TSC_RUN_ROOT}"
cat <<EOF
[Stage4.1R3] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1R3] source_stage4_0_run=${SOURCE_STAGE4_0_RUN}
[Stage4.1R3] run_dir=${RUN_DIR}
[Stage4.1R3] config=${CONFIG}
[Stage4.1R3] command=${COMMAND}
[Stage4.1R3] backend=${BACKEND}
[Stage4.1R3] resume=${RESUME}
[Stage4.1R3] workers=${STAGE4_1R3_WORKERS}
[Stage4.1R3] python=${PYTHON_BIN}
[Stage4.1R3] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1R3] TSC_WORKSPACE_ROOT=${STAGE4_1R3_TSC_WORKSPACE_ROOT}
[Stage4.1R3] TSC_RUN_ROOT=${STAGE4_1R3_TSC_RUN_ROOT}
[Stage4.1R3] Campaign capacity is fixed at ${STAGE4_1R3_WORKERS} workers (default 128); no silent fallback is allowed.
[Stage4.1R3] Stage3.4 target library, selected scale, 175x105 Jacobian, and hard gate remain frozen.
[Stage4.1R3] Clean sensors use the exact Stage3.4 measurement path; noisy/delayed sensors use a control-aware residual observer.
[Stage4.1R3] A 30-rollout integration regression is followed by a 64-rollout observer/anti-windup ablation; either failure stops the expensive robustness campaign.
[Stage4.1R3] Physical 14-coil inverse scheduling, action-delay queue prediction, phase-aware continuation, and anti-windup are retained.
[Stage4.1R3] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1R3] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF
ARGS=(--config "${CONFIG}" --source-stage4-0-run "${SOURCE_STAGE4_0_RUN}" --run-dir "${RUN_DIR}" --backend "${BACKEND}" --command "${COMMAND}")
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1r3_control_aware_robustness.py" "${ARGS[@]}"
