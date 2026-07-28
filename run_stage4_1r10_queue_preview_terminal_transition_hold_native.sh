#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r10_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r10_shell_common.sh"
stage4_1r10_validate_common
SOURCE_R9="$(stage4_1r10_find_source_r9)" || {
  echo "ERROR: no complete Stage4.1R9 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R10_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R10_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r10_new_run_dir)"
fi
if [[ "${STAGE4_1R10_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r10_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r10_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r10_export_runtime
if [[ "${STAGE4_1R10_BACKEND}" == "ray" && "${STAGE4_1R10_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R10] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R10] source_stage4_1r9_run=%s\n' "${SOURCE_R9}"
printf '[Stage4.1R10] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R10] config=%s\n' "${STAGE4_1R10_CONFIG}"
printf '[Stage4.1R10] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R10_COMMAND}" "${STAGE4_1R10_BACKEND}" "${STAGE4_1R10_RESUME}" "${STAGE4_1R10_WORKERS}"
printf '[Stage4.1R10] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R10_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R10] R9 runtime/solver/queue were healthy, but all delay=1/2 policies failed before terminal commands could act.\n'
printf '[Stage4.1R10] The exact physical and applied-command prefix through 350 ms is frozen; only commands still unapplied at 350 ms are causally replaced at their original issue times.\n'
printf '[Stage4.1R10] Development uses nominal only, RZ_p10_m10 is a disjoint holdout, and untrusted calibration cannot start control.\n'
printf '[Stage4.1R10] This remains a finite clean-measurement digital-twin test, not restart, hidden-history, plant-mismatch, continuous-parameter, noise, or deployment validation.\n'
printf '[Stage4.1R10] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across hidden histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R10_CONFIG}"
  --source-stage4-1r9-run "${SOURCE_R9}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R10_COMMAND}"
  --backend "${STAGE4_1R10_BACKEND}"
)
[[ "${STAGE4_1R10_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R10_PYTHON}" scripts/stage4_1r10_queue_preview_terminal_transition_hold.py "${args[@]}"
