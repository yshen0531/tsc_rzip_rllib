#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r15_shell_common.sh"
stage4_1r15_validate_common
SOURCE_R14="$(stage4_1r15_find_source_r14)" || { echo "ERROR: no complete Stage4.1R14 source run found" >&2; exit 1; }
if [[ -n "${STAGE4_1R15_RUN_DIR:-}" ]]; then RUN_DIR="${STAGE4_1R15_RUN_DIR}"; else RUN_DIR="$(stage4_1r15_new_run_dir)"; fi
if [[ "${STAGE4_1R15_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_1r15_state.json" ]] || { echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r15_state.json" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_1r15_export_runtime
if [[ "${STAGE4_1R15_BACKEND}" == "ray" && "${STAGE4_1R15_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then ray stop --force >/dev/null 2>&1 || true; fi
printf '[Stage4.1R15] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R15] source_stage4_1r14_run=%s\n' "${SOURCE_R14}"
printf '[Stage4.1R15] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R15] config=%s\n' "${STAGE4_1R15_CONFIG}"
printf '[Stage4.1R15] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R15_COMMAND}" "${STAGE4_1R15_BACKEND}" "${STAGE4_1R15_RESUME}" "${STAGE4_1R15_WORKERS}"
printf '[Stage4.1R15 R15a] Direct R14 source fingerprinting is active; nested R13 provenance is validated independently.\n'
printf '[Stage4.1R15] R14 ran normally but all 24 cases rebounded after state 34 and failed final speed; this is a model-horizon/tail-semantic problem, not a runtime failure.\n'
printf '[Stage4.1R15] R15 is identification-only: fit/cross-validate the bounded R13/R14 local response bank, then validate with 32 preregistered zero-net TSC probes.\n'
printf '[Stage4.1R15] No controller is selected, no formal closure is claimed, and the 250/350 and 270/370 ms timing contracts remain immutable.\n'
printf '[Stage4.1R15] R10/R11 long horizons remain auxiliary only; Stage4.2R1 was not run or reused; BC/DAgger/RL are not started.\n'
printf '[Stage4.1R15] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(--config "${STAGE4_1R15_CONFIG}" --source-stage4-1r14-run "${SOURCE_R14}" --run-dir "${RUN_DIR}" --command "${STAGE4_1R15_COMMAND}" --backend "${STAGE4_1R15_BACKEND}")
[[ "${STAGE4_1R15_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_1R15_PYTHON}" scripts/stage4_1r15_bounded_early_braking_local_response_identification.py "${args[@]}"
