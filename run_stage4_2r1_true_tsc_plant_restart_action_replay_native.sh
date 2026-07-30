#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r1_shell_common.sh"
stage4_2r1_validate_common
SOURCE_R17="$(stage4_2r1_find_source_r17)" || {
  echo "ERROR: no complete Stage4.1R17 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_2R1_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R1_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r1_new_run_dir)"
fi
if [[ "${STAGE4_2R1_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r1_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r1_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r1_export_runtime
if [[ "${STAGE4_2R1_BACKEND}" == "ray" && "${STAGE4_2R1_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.2R1] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R1] source_stage4_1r17_run=%s\n' "${SOURCE_R17}"
printf '[Stage4.2R1] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R1] config=%s\n' "${STAGE4_2R1_CONFIG}"
printf '[Stage4.2R1] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_2R1_COMMAND}" "${STAGE4_2R1_BACKEND}" "${STAGE4_2R1_RESUME}" "${STAGE4_2R1_WORKERS}"
printf '[Stage4.2R1 R1a] Capture exceptions preserve partial trajectories; shape mismatches are finite structured JSON; legacy successful snapshots remain resume-safe.\n'
printf '[Stage4.2R1] python=%s RAY_TMPDIR=%s\n' "${STAGE4_2R1_PYTHON}" "${RAY_TMPDIR}"
printf '[Stage4.2R1] R17 original timing is frozen: slew 1.0/1.1 arrives by 250 ms and holds through 350 ms; slew 0.9 arrives by 270 ms and holds through 370 ms.\n'
printf '[Stage4.2R1] This stage isolates authentic TSC plant-state restart: exact R17 expert actions are replayed, sprsina plus full coil/wire state is captured at 200 ms, and a fresh TSC process replays the remaining suffix.\n'
printf '[Stage4.2R1] Plant restart fidelity and formal-contract preservation are reported separately. Controller observer/integrator/queue checkpoint replay is deliberately not performed in R1.\n'
printf '[Stage4.2R1] The old unrun R11-based Stage4.2R1 package is not reused. R10/R11 750 ms/2 s trajectories remain auxiliary diagnostics only.\n'
printf '[Stage4.2R1] This does not validate unseen hidden histories, new targets, plant mismatch, continuous actuator changes, noise, disturbances, deployment, BC, DAgger or RL.\n'
printf '[Stage4.2R1] Final task remains causal safe arrival, deceleration, disturbance recovery and long hold across initial states, hidden vessel/eddy histories, targets, continuous plant/actuator changes, noise and unknown delay.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R1_CONFIG}"
  --source-stage4-1r17-run "${SOURCE_R17}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R1_COMMAND}"
  --backend "${STAGE4_2R1_BACKEND}"
)
[[ "${STAGE4_2R1_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R1_PYTHON}" scripts/stage4_2r1_true_tsc_plant_restart_action_replay.py "${args[@]}"
