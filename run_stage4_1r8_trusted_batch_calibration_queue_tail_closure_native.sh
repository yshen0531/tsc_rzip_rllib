#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r8_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r8_shell_common.sh"
stage4_1r8_validate_common
SOURCE_R7="$(stage4_1r8_find_source_r7)" || { echo "ERROR: no complete Stage4.1R7 source run found" >&2; exit 1; }
if [[ -n "${STAGE4_1R8_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R8_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r8_new_run_dir)"
fi
if [[ "${STAGE4_1R8_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r8_state.json" ]] || { echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r8_state.json" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_1r8_export_runtime
if [[ "${STAGE4_1R8_BACKEND}" == "ray" && "${STAGE4_1R8_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R8] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R8] source_stage4_1r7_run=%s\n' "${SOURCE_R7}"
printf '[Stage4.1R8] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R8] config=%s\n' "${STAGE4_1R8_CONFIG}"
printf '[Stage4.1R8] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R8_COMMAND}" "${STAGE4_1R8_BACKEND}" "${STAGE4_1R8_RESUME}" "${STAGE4_1R8_WORKERS}"
printf '[Stage4.1R8] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R8_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R8] Untrusted calibration cannot start main control; the 350 ms pending action queue is drained before zero-increment tail actions.\n'
printf '[Stage4.1R8] Main MPC/observer/library/Jacobian remain frozen. This is still a finite digital-twin envelope, not restart/deployment validation.\n'
printf '[Stage4.1R8] Final task remains causal safe arrival, deceleration, recovery and long hold across hidden histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R8_CONFIG}"
  --source-stage4-1r7-run "${SOURCE_R7}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R8_COMMAND}"
  --backend "${STAGE4_1R8_BACKEND}"
)
[[ "${STAGE4_1R8_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R8_PYTHON}" scripts/stage4_1r8_trusted_batch_calibration_queue_tail_closure.py "${args[@]}"
