#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r2_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r2_shell_common.sh"
stage4_2r2_validate_common
SOURCE_R1="$(stage4_2r2_find_source_r1)" || {
  echo "ERROR: no complete certified Stage4.2R1 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_2R2_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R2_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r2_new_run_dir)"
fi
if [[ "${STAGE4_2R2_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r2_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r2_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r2_export_runtime
if [[ "${STAGE4_2R2_BACKEND}" == "ray" && "${STAGE4_2R2_RESUME}" == "0" ]] && command -v ray >/dev/null 2>&1; then
  ray stop --force >/dev/null 2>&1 || true
fi
printf '[Stage4.2R2] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R2] source_stage4_2r1_run=%s\n' "${SOURCE_R1}"
printf '[Stage4.2R2] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R2] config=%s\n' "${STAGE4_2R2_CONFIG}"
printf '[Stage4.2R2] command=%s backend=%s resume=%s workers=%s\n' "${STAGE4_2R2_COMMAND}" "${STAGE4_2R2_BACKEND}" "${STAGE4_2R2_RESUME}" "${STAGE4_2R2_WORKERS}"
printf '[Stage4.2R2] Before any new TSC process, a no-gotsc audit must recompute all expert suffix actions exactly from causal checkpoint state.\n'
printf '[Stage4.2R2] No recorded future action or measurement is stored in or exposed to the controller checkpoint. Frozen time-varying R17 policy parameters remain controller code.\n'
printf '[Stage4.2R2] Formal timing remains 250/350 ms for slew 1.0/1.1 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R2] This validates same-source persistent controller restart only; hidden-history, initial-state, target, continuous-parameter, noise, disturbance and long-hold robustness remain unvalidated.\n'
printf '[Stage4.2R2] Large raw results remain on the server. Python postprocessing produces compact audit JSON/CSV/manifests for transfer.\n'
printf '[Stage4.2R2] BC, DAgger and residual RL remain forbidden until the reliable MPC expert roadmap is complete.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R2_CONFIG}"
  --source-stage4-2r1-run "${SOURCE_R1}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R2_COMMAND}"
  --backend "${STAGE4_2R2_BACKEND}"
)
[[ "${STAGE4_2R2_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R2_PYTHON}" \
  scripts/stage4_2r2_persistent_controller_checkpoint_replay.py "${args[@]}"
