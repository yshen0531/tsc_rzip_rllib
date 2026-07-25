#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1_shell_common.sh"
stage41_project_init
stage41_find_python
stage41_runtime_env
CONFIG="${STAGE4_1_CONFIG:-${PROJECT_DIR}/configs/stage4_1_delay_gain_phase_robustness_350ms.json}"
CONFIG="$(stage41_abspath "${CONFIG}")"
[[ -f "${CONFIG}" ]] || stage41_die "Stage4.1 config not found: ${CONFIG}"
COMMAND="${STAGE4_1_COMMAND:-all}"
case "${COMMAND}" in all|prepare|regression|recovery|structured|noise|history|restart|confirm|analyze) ;; *) stage41_die "invalid STAGE4_1_COMMAND=${COMMAND}" ;; esac
BACKEND="${STAGE4_1_BACKEND:-ray}"
case "${BACKEND}" in ray|serial) ;; *) stage41_die "invalid STAGE4_1_BACKEND=${BACKEND}" ;; esac
RESUME="${STAGE4_1_RESUME:-0}"
case "${RESUME}" in 0|1) ;; *) stage41_die "STAGE4_1_RESUME must be 0 or 1" ;; esac
if [[ -n "${STAGE4_1_RUN_DIR:-}" ]]; then RUN_DIR="$(stage41_abspath "${STAGE4_1_RUN_DIR}")"
else
  STAMP="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="${PROJECT_DIR}/stage4_1_runs/stage4_1_delay_gain_phase_robustness_350ms_${STAMP}"
  suffix=0; while [[ -e "${RUN_DIR}" ]]; do suffix=$((suffix+1)); RUN_DIR="${PROJECT_DIR}/stage4_1_runs/stage4_1_delay_gain_phase_robustness_350ms_${STAMP}_${suffix}"; done
fi
export STAGE4_1_RUN_DIR="${RUN_DIR}"
mkdir -p "${PROJECT_DIR}/stage4_1_runs" "${PROJECT_DIR}/logs/nohup"
if [[ "${RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1_state.json" ]] || stage41_die "resume state missing: ${RUN_DIR}/stage4_1_state.json"
  stage41_source_from_existing_run "${RUN_DIR}"
else
  if [[ -d "${RUN_DIR}" ]] && find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then stage41_die "fresh run directory is not empty: ${RUN_DIR}"; fi
  mkdir -p "${RUN_DIR}"
fi
stage41_detect_source
printf '%s\n' "${RUN_DIR}" > "${PROJECT_DIR}/stage4_1_runs/latest_stage4_1_run.txt"
cleanup_on_exit() { local status=$?; trap - EXIT; set +e; stage41_ray_stop; stage41_cleanup_runtime; exit "${status}"; }
trap cleanup_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
stage41_ray_stop
stage41_cleanup_runtime
mkdir -p "${TMPDIR}" "${STAGE4_1_TSC_RUN_ROOT}"
cat <<EOF
[Stage4.1] user=$(id -un) host=$(hostname) pwd=${PROJECT_DIR}
[Stage4.1] source_stage4_0_run=${SOURCE_STAGE4_0_RUN}
[Stage4.1] run_dir=${RUN_DIR}
[Stage4.1] config=${CONFIG}
[Stage4.1] command=${COMMAND}
[Stage4.1] backend=${BACKEND}
[Stage4.1] resume=${RESUME}
[Stage4.1] workers=${STAGE4_1_WORKERS}
[Stage4.1] python=${PYTHON_BIN}
[Stage4.1] RAY_TMPDIR=${RAY_TMPDIR}
[Stage4.1] TSC_WORKSPACE_ROOT=${STAGE4_1_TSC_WORKSPACE_ROOT}
[Stage4.1] TSC_RUN_ROOT=${STAGE4_1_TSC_RUN_ROOT}
[Stage4.1] Campaign capacity is fixed at ${STAGE4_1_WORKERS} workers (default 128); no silent fallback is allowed.
[Stage4.1] Stage3.4 target library, selected scale, 175x105 Jacobian, and hard gate remain frozen.
[Stage4.1] Controller wrapper adds alpha-beta state estimation, action-delay queue prediction, gain/slew scheduling, nominal pre-compensation, and phase-aware continuation.
[Stage4.1] Adaptive disturbances continue until an open-loop failure boundary is reached; noise is evaluated with multiple independent seeds and category-specific gates.
[Stage4.1] Residual Markdown files elsewhere in the project are ignored by package verification.
[Stage4.1] Final task remains robust causal control across initial states, targets, hidden dynamics, plant uncertainty, noise, and delay.
EOF
ARGS=(--config "${CONFIG}" --source-stage4-0-run "${SOURCE_STAGE4_0_RUN}" --run-dir "${RUN_DIR}" --backend "${BACKEND}" --command "${COMMAND}")
if [[ "${RESUME}" == 1 ]]; then ARGS+=(--resume); else ARGS+=(--no-resume); fi
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_1_delay_gain_phase_robustness.py" "${ARGS[@]}"
