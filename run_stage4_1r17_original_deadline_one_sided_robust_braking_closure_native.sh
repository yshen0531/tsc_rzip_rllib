#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_1r17_shell_common.sh"
stage4_1r17_validate_common
SOURCE_R16="$(stage4_1r17_find_source_r16)" || { echo "ERROR: no complete Stage4.1R16 source run found" >&2; exit 1; }
if [[ -n "${STAGE4_1R17_RUN_DIR:-}" ]]; then RUN_DIR="${STAGE4_1R17_RUN_DIR}"; else RUN_DIR="$(stage4_1r17_new_run_dir)"; fi
if [[ "${STAGE4_1R17_RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_1r17_state.json" ]] || { echo "ERROR: resume state missing: ${RUN_DIR}/stage4_1r17_state.json" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_1r17_export_runtime
if [[ "${STAGE4_1R17_BACKEND}" == ray && "${STAGE4_1R17_RESUME}" == 0 ]] && command -v ray >/dev/null 2>&1; then ray stop --force >/dev/null 2>&1 || true; fi
printf '[Stage4.1R17] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.1R17] source_stage4_1r16_run=%s\n' "${SOURCE_R16}"
printf '[Stage4.1R17] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.1R17] config=%s\n' "${STAGE4_1R17_CONFIG}"
printf '[Stage4.1R17] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_1R17_COMMAND}" "${STAGE4_1R17_BACKEND}" "${STAGE4_1R17_RESUME}" "${STAGE4_1R17_WORKERS}"
printf '[Stage4.1R17 R17a] Canonical R15 output-vector contract is active for states 23--37; legacy R17 manifests and successful Oracle raw are reusable with resume=1.\n'
printf '[Stage4.1R17] R16 ran normally. Its symmetric large-amplitude envelope failed, but all 16 one-sided braking rollouts passed runtime and model guards.\n'
printf '[Stage4.1R17] Delay=1 retains the real-TSC 6x source trajectory; delay=2 tests one preregistered 7x braking candidate with 0.105 peak component. No posthoc 7.5x/8x fallback is permitted.\n'
printf '[Stage4.1R17] Exact per-step requested/applied probe equality is required; the weaker R16 max/count-only guard is not reused.\n'
printf '[Stage4.1R17] Formal timing remains immutable: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.1R17] This is a finite clean two-target static-delay patch, not bidirectional-model, restart, hidden-history, continuous-parameter, noisy-sensing, disturbance-recovery or deployment validation.\n'
printf '[Stage4.1R17] Stage4.2R1, BC, DAgger and RL are not run or reused.\n'
printf '[Stage4.1R17] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(--config "${STAGE4_1R17_CONFIG}" --source-stage4-1r16-run "${SOURCE_R16}" --run-dir "${RUN_DIR}" --command "${STAGE4_1R17_COMMAND}" --backend "${STAGE4_1R17_BACKEND}")
[[ "${STAGE4_1R17_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_1R17_PYTHON}" scripts/stage4_1r17_original_deadline_one_sided_robust_braking_closure.py "${args[@]}"
