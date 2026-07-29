#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r13_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r13_shell_common.sh"
stage4_1r13_validate_common
SOURCE_R12="$(stage4_1r13_find_source_r12)" || {
  echo "ERROR: no complete Stage4.1R12 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R13_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R13_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r13_new_run_dir)"
fi
if [[ "${STAGE4_1R13_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r13_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r13_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r13_export_runtime
if [[ "${STAGE4_1R13_BACKEND}" == "ray" && "${STAGE4_1R13_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R13] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R13] source_stage4_1r12_run=%s\n' "${SOURCE_R12}"
printf '[Stage4.1R13] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R13] config=%s\n' "${STAGE4_1R13_CONFIG}"
printf '[Stage4.1R13] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R13_COMMAND}" "${STAGE4_1R13_BACKEND}" "${STAGE4_1R13_RESUME}" "${STAGE4_1R13_WORKERS}"
printf '[Stage4.1R13] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R13_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R13] Formal timing remains immutable: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.1R13] R12 ran correctly but its first physical effects at 280--350 ms were structurally too late for endpoint-late-speed failures already present at 270 ms.\n'
printf '[Stage4.1R13] Only the four weak-slew delay=1/2 paths may change; causal first physical effects are tested at 200--260 ms with issue times shifted earlier only by the trusted delay queue.\n'
printf '[Stage4.1R13] Both required targets participate in finite-grid policy selection; no unseen-target generalization is claimed. The fourteen already-passing paths remain source-exact and are not rerun.\n'
printf '[Stage4.1R13] No arrival deadline, scoring horizon, 30 mm gate, 0.1 m/s gate, or Ip gate is relaxed. R10/R11 long horizons remain diagnostics only; Stage4.2R1 was not run or reused.\n'
printf '[Stage4.1R13] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R13_CONFIG}"
  --source-stage4-1r12-run "${SOURCE_R12}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R13_COMMAND}"
  --backend "${STAGE4_1R13_BACKEND}"
)
[[ "${STAGE4_1R13_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R13_PYTHON}" scripts/stage4_1r13_original_deadline_delay_pipeline_early_braking.py "${args[@]}"
