#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r16_shell_common.sh"
stage4_1r16_validate_common
SOURCE_R15B="$(stage4_1r16_find_source_r15b)" || { echo "ERROR: no complete Stage4.1R15B source run found" >&2; exit 1; }
if [[ -n "${STAGE4_1R16_RUN_DIR:-}" ]]; then RUN_DIR="${STAGE4_1R16_RUN_DIR}"; else RUN_DIR="$(stage4_1r16_new_run_dir)"; fi
if [[ "${STAGE4_1R16_RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r16_state.json" ]] || { echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r16_state.json" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_1r16_export_runtime
if [[ "${STAGE4_1R16_BACKEND}" == ray && "${STAGE4_1R16_RESUME}" == 0 ]] && command -v ray >/dev/null 2>&1; then ray stop --force >/dev/null 2>&1 || true; fi
printf '[Stage4.1R16] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R16] source_stage4_1r15b_run=%s\n' "${SOURCE_R15B}"
printf '[Stage4.1R16] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R16] config=%s\n' "${STAGE4_1R16_CONFIG}"
printf '[Stage4.1R16] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R16_COMMAND}" "${STAGE4_1R16_BACKEND}" "${STAGE4_1R16_RESUME}" "${STAGE4_1R16_WORKERS}"
printf '[Stage4.1R16] R15B is a genuine 32/32 small-signal superposition validation, but its externally validated 0.015-component envelope does not close the two RZ weak-slew paths.\n'
printf '[Stage4.1R16] The 1x/2x/4x/6x plus-minus amplitude ladder is preregistered. The fixed 6x braking direction is not accepted unless real TSC validates safety, symmetry, scaling, prediction and all four original-deadline paths.\n'
printf '[Stage4.1R16] Formal timing is immutable: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.1R16] No unseen-target, continuous-parameter, restart, noisy-sensing or deployment robustness is claimed; Stage4.2R1, BC, DAgger and RL are not run or reused.\n'
printf '[Stage4.1R16] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(--config "${STAGE4_1R16_CONFIG}" --source-stage4-1r15b-run "${SOURCE_R15B}" --run-dir "${RUN_DIR}" --command "${STAGE4_1R16_COMMAND}" --backend "${STAGE4_1R16_BACKEND}")
[[ "${STAGE4_1R16_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_1R16_PYTHON}" scripts/stage4_1r16_amplitude_certified_probe_derived_braking_closure.py "${args[@]}"
