#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r14_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r14_shell_common.sh"
stage4_1r14_validate_common
SOURCE_R13="$(stage4_1r14_find_source_r13)" || {
  echo "ERROR: no complete Stage4.1R13 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R14_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R14_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r14_new_run_dir)"
fi
if [[ "${STAGE4_1R14_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r14_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r14_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r14_export_runtime
if [[ "${STAGE4_1R14_BACKEND}" == "ray" && "${STAGE4_1R14_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R14] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R14] source_stage4_1r13_run=%s\n' "${SOURCE_R13}"
printf '[Stage4.1R14] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R14] config=%s\n' "${STAGE4_1R14_CONFIG}"
printf '[Stage4.1R14] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R14_COMMAND}" "${STAGE4_1R14_BACKEND}" "${STAGE4_1R14_RESUME}" "${STAGE4_1R14_WORKERS}"
printf '[Stage4.1R14] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R14_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R14] Formal timing is immutable: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.1R14] R13 ran correctly but its scalar onset scan handed off to a zero-nominal, reset-integral residual regulator; RZ_p10_m10 failed 7/7 for each delay while the first two software correction modes were frequently bounded.\n'
printf '[Stage4.1R14] The first physical effect is fixed at state 23; no onset or horizon is rescanned. The target-conditioned Stage3.4 nominal trajectory/feedforward and checkpoint integral are retained.\n'
printf '[Stage4.1R14] Only an explicit state-24--27 velocity-weight multiplier and bounded software correction scale are compared inside the same delay-aware 175x105 MPC.\n'
printf '[Stage4.1R14] Both required targets participate in finite-grid selection; no unseen-target generalization is claimed. The fourteen already-passing paths remain source-exact and are not rerun.\n'
printf '[Stage4.1R14] No arrival deadline, scoring horizon, 30 mm gate, 0.1 m/s gate, or Ip gate is relaxed. R10/R11 long horizons remain diagnostics only; Stage4.2R1 was not run or reused.\n'
printf '[Stage4.1R14] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R14_CONFIG}"
  --source-stage4-1r13-run "${SOURCE_R13}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R14_COMMAND}"
  --backend "${STAGE4_1R14_BACKEND}"
)
[[ "${STAGE4_1R14_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R14_PYTHON}" scripts/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py "${args[@]}"
