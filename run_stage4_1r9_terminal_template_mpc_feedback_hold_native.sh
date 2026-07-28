#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r9_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r9_shell_common.sh"
stage4_1r9_validate_common
SOURCE_R8="$(stage4_1r9_find_source_r8)" || {
  echo "ERROR: no complete Stage4.1R8 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R9_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R9_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r9_new_run_dir)"
fi
if [[ "${STAGE4_1R9_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r9_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r9_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r9_export_runtime
if [[ "${STAGE4_1R9_BACKEND}" == "ray" && "${STAGE4_1R9_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R9] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R9] source_stage4_1r8_run=%s\n' "${SOURCE_R8}"
printf '[Stage4.1R9] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R9] config=%s\n' "${STAGE4_1R9_CONFIG}"
printf '[Stage4.1R9] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R9_COMMAND}" "${STAGE4_1R9_BACKEND}" "${STAGE4_1R9_RESUME}" "${STAGE4_1R9_WORKERS}"
printf '[Stage4.1R9] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R9_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R9 R9a] Complete R8 metric-policy contract is active; existing successful raw rollouts remain reusable under resume=1.\n'
printf '[Stage4.1R9] The first 350 ms MPC/observer/library/Jacobian are frozen. Only the failed open-loop tail is replaced by continuously streaming delay-aware terminal feedback.\n'
printf '[Stage4.1R9] Candidate selection uses nominal only; RZ_p10_m10 is a disjoint holdout. Untrusted calibration cannot start control and no online handover is used.\n'
printf '[Stage4.1R9] This remains a finite clean-measurement digital-twin test, not true restart, plant-mismatch, continuous-parameter, or deployment validation.\n'
printf '[Stage4.1R9] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across hidden histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R9_CONFIG}"
  --source-stage4-1r8-run "${SOURCE_R8}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R9_COMMAND}"
  --backend "${STAGE4_1R9_BACKEND}"
)
[[ "${STAGE4_1R9_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R9_PYTHON}" scripts/stage4_1r9_terminal_template_mpc_feedback_hold.py "${args[@]}"
