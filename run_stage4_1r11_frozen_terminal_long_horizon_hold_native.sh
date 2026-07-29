#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r11_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r11_shell_common.sh"
stage4_1r11_validate_common
SOURCE_R10="$(stage4_1r11_find_source_r10)" || {
  echo "ERROR: no complete Stage4.1R10 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R11_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R11_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r11_new_run_dir)"
fi
if [[ "${STAGE4_1R11_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r11_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r11_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r11_export_runtime
if [[ "${STAGE4_1R11_BACKEND}" == "ray" && "${STAGE4_1R11_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R11] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R11] source_stage4_1r10_run=%s\n' "${SOURCE_R10}"
printf '[Stage4.1R11] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R11] config=%s\n' "${STAGE4_1R11_CONFIG}"
printf '[Stage4.1R11] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R11_COMMAND}" "${STAGE4_1R11_BACKEND}" "${STAGE4_1R11_RESUME}" "${STAGE4_1R11_WORKERS}"
printf '[Stage4.1R11] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R11_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R11] R10 finite 750 ms closure is frozen; no policy retuning and no new favorable endpoint search are allowed.\n'
printf '[Stage4.1R11] The complete R10 physics/issued/applied/preview/terminal prefix through 750 ms must remain bit-exact.\n'
printf '[Stage4.1R11] The same two targets and static 3x3 delay/slew grid are extended to a fixed 2000 ms clean hold from the inherited 650 ms hold start.\n'
printf '[Stage4.1R11] This is still not true restart, hidden-history, continuous-parameter, plant-mismatch, noisy-sensing, or deployment validation.\n'
printf '[Stage4.1R11] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across hidden histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R11_CONFIG}"
  --source-stage4-1r10-run "${SOURCE_R10}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R11_COMMAND}"
  --backend "${STAGE4_1R11_BACKEND}"
)
[[ "${STAGE4_1R11_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R11_PYTHON}" scripts/stage4_1r11_frozen_terminal_long_horizon_hold.py "${args[@]}"
