#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c_shell_common.sh"
stage4_2r3c_validate_common
SOURCE_R3B="$(stage4_2r3c_find_source_r3b)" || exit 1
if [[ -n "${STAGE4_2R3C_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3c_new_run_dir)"
fi
if [[ "${STAGE4_2R3C_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3c_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c_export_runtime
printf '[Stage4.2R3c] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c] source_stage4_2r3b_run=%s\n' "${SOURCE_R3B}"
printf '[Stage4.2R3c] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3c] config=%s\n' "${STAGE4_2R3C_CONFIG}"
printf '[Stage4.2R3c] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3C_COMMAND}" "${STAGE4_2R3C_BACKEND}" \
  "${STAGE4_2R3C_RESUME}" "${STAGE4_2R3C_WORKERS}"
printf '[Stage4.2R3c] Offline gate requires original-start R17 phase 0 and exact action preservation before real TSC.\n'
printf '[Stage4.2R3c] Task/formal time starts at zero; only the nominal/model phase is selected from current visible R/Z/Ip.\n'
printf '[Stage4.2R3c] The exact locked R3b four-pair snapshots are a development set, not independent confirmation.\n'
printf '[Stage4.2R3c] Full wire current remains post-action audit telemetry and is forbidden from phase selection/control.\n'
printf '[Stage4.2R3c] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3c] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C_COMMAND}"
  --backend "${STAGE4_2R3C_BACKEND}"
)
[[ "${STAGE4_2R3C_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3C_PYTHON}" \
  scripts/stage4_2r3c_visible_state_phase_aligned_mpc.py "${args[@]}"
