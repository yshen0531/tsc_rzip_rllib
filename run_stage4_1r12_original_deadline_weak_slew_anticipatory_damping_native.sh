#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_1r12_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_1r12_shell_common.sh"
stage4_1r12_validate_common
SOURCE_R11="$(stage4_1r12_find_source_r11)" || {
  echo "ERROR: no complete Stage4.1R11 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_1R12_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_1R12_RUN_DIR}"
else
  RUN_DIR="$(stage4_1r12_new_run_dir)"
fi
if [[ "${STAGE4_1R12_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r12_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r12_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_1r12_export_runtime
if [[ "${STAGE4_1R12_BACKEND}" == "ray" && "${STAGE4_1R12_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.1R12] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R12] source_stage4_1r11_run=%s\n' "${SOURCE_R11}"
printf '[Stage4.1R12] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R12] config=%s\n' "${STAGE4_1R12_CONFIG}"
printf '[Stage4.1R12] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R12_COMMAND}" "${STAGE4_1R12_BACKEND}" "${STAGE4_1R12_RESUME}" "${STAGE4_1R12_WORKERS}"
printf '[Stage4.1R12] python=%s RAY_TMPDIR=%s\n' "${STAGE4_1R12_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.1R12] Formal timing is immutable: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.1R12] R11 2 s results are auxiliary diagnostics only. Stage4.2R1 was not run and is not reused.\n'
printf '[Stage4.1R12] Only the four weak-slew delay=1/2 failures are modified; candidate first physical effects span 280--350 ms.\n'
printf '[Stage4.1R12] Commands may be issued earlier only because of the known delay queue; source physics through the 270 ms arrival deadline must remain bit-exact.\n'
printf '[Stage4.1R12] The fourteen already-passing paths are reused unchanged and are not rerun.\n'
printf '[Stage4.1R12] No arrival deadline, scoring horizon, 30 mm gate, 0.1 m/s gate, or Ip gate is relaxed.\n'
printf '[Stage4.1R12] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_1R12_CONFIG}"
  --source-stage4-1r11-run "${SOURCE_R11}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_1R12_COMMAND}"
  --backend "${STAGE4_1R12_BACKEND}"
)
[[ "${STAGE4_1R12_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R12_PYTHON}" scripts/stage4_1r12_original_deadline_weak_slew_anticipatory_damping.py "${args[@]}"
