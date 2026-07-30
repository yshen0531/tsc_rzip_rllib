#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c2_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c2_shell_common.sh"
stage4_2r3c2_validate_common
SOURCE_R3B="$(stage4_2r3c2_find_source_r3b)" || exit 1
SOURCE_R3C="$(stage4_2r3c2_find_source_r3c)" || exit 1
SOURCE_R3C1="$(stage4_2r3c2_find_source_r3c1)" || exit 1
if [[ -n "${STAGE4_2R3C2_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C2_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3c2_new_run_dir)"
fi
if [[ "${STAGE4_2R3C2_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c2_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3c2_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c2_export_runtime
printf '[Stage4.2R3c2] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c2] source_stage4_2r3b_run=%s\n' "${SOURCE_R3B}"
printf '[Stage4.2R3c2] source_stage4_2r3c_run=%s\n' "${SOURCE_R3C}"
printf '[Stage4.2R3c2] source_stage4_2r3c1_run=%s\n' "${SOURCE_R3C1}"
printf '[Stage4.2R3c2] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3c2] config=%s\n' "${STAGE4_2R3C2_CONFIG}"
printf '[Stage4.2R3c2] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3C2_COMMAND}" "${STAGE4_2R3C2_BACKEND}" \
  "${STAGE4_2R3C2_RESUME}" "${STAGE4_2R3C2_WORKERS}"
printf '[Stage4.2R3c2] Offline gate requires original-start R17 phase 0 and exact action preservation before real TSC.\n'
printf '[Stage4.2R3c2] Phase zero preserves R17; every nonzero visible phase starts target-state regulation at task step zero.\n'
printf '[Stage4.2R3c2] Source actions/results, pair/history labels, source/current wire currents and current-run future values are forbidden from the controller.\n'
printf '[Stage4.2R3c2] The exact locked R3b four-pair snapshots are a development set, not independent confirmation.\n'
printf '[Stage4.2R3c2] Full wire current remains post-action audit telemetry and is forbidden from phase selection/control.\n'
printf '[Stage4.2R3c2] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3c2] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C2_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C2_COMMAND}"
  --backend "${STAGE4_2R3C2_BACKEND}"
)
[[ "${STAGE4_2R3C2_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3C2_PYTHON}" \
  scripts/stage4_2r3c2_restart_target_state_regulation_mpc.py "${args[@]}"
