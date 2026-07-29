#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r15b_shell_common.sh"
stage4_1r15b_validate_common
SOURCE_R15="$(stage4_1r15b_find_source_r15)" || { echo "ERROR: no complete Stage4.1R15 source run found" >&2; exit 1; }
if [[ -n "${STAGE4_1R15B_RUN_DIR:-}" ]]; then RUN_DIR="${STAGE4_1R15B_RUN_DIR}"; else RUN_DIR="$(stage4_1r15b_new_run_dir)"; fi
if [[ "${STAGE4_1R15B_RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r15b_state.json" ]] || { echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r15b_state.json" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_1r15b_export_runtime
if [[ "${STAGE4_1R15B_BACKEND}" == ray && "${STAGE4_1R15B_RESUME}" == 0 ]] && command -v ray >/dev/null 2>&1; then ray stop --force >/dev/null 2>&1 || true; fi
printf '[Stage4.1R15B] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R15B] source_stage4_1r15_run=%s\n' "${SOURCE_R15}"
printf '[Stage4.1R15B] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R15B] config=%s\n' "${STAGE4_1R15B_CONFIG}"
printf '[Stage4.1R15B] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R15B_COMMAND}" "${STAGE4_1R15B_BACKEND}" "${STAGE4_1R15B_RESUME}" "${STAGE4_1R15B_WORKERS}"
printf '[Stage4.1R15B] R15 ran normally: 32/32 runtime guards passed, but one externally validated model prediction exceeded the preregistered final-speed error limit by 0.350 mm/s.\n'
printf '[Stage4.1R15B] This stage is identification-only. It derives odd finite-difference responses from the R15 plus/minus probes and validates superposition with 32 new orthogonal Hadamard combination probes.\n'
printf '[Stage4.1R15B] Formal 250/350 and 270/370 ms timing remains immutable; no controller is selected and no failed source probe is waived.\n'
printf '[Stage4.1R15B] Stage4.2R1, BC, DAgger and RL are not run or reused.\n'
printf '[Stage4.1R15B] Final task remains causal safe arrival, deceleration, recovery and long hold across initial states, hidden histories, targets, plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(--config "${STAGE4_1R15B_CONFIG}" --source-stage4-1r15-run "${SOURCE_R15}" --run-dir "${RUN_DIR}" --command "${STAGE4_1R15B_COMMAND}" --backend "${STAGE4_1R15B_BACKEND}")
[[ "${STAGE4_1R15B_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_1R15B_PYTHON}" scripts/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation.py "${args[@]}"
