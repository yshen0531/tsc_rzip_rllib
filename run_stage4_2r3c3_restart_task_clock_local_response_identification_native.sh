#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3_shell_common.sh"
stage4_2r3c3_validate_common
SOURCE_R3B="$(stage4_2r3c3_find_source_r3b)" || exit 1
SOURCE_R3C="$(stage4_2r3c3_find_source_r3c)" || exit 1
SOURCE_R3C1="$(stage4_2r3c3_find_source_r3c1)" || exit 1
SOURCE_R3C2="$(stage4_2r3c3_find_source_r3c2)" || exit 1
if [[ -n "${STAGE4_2R3C3_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C3_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3c3_new_run_dir)"
fi
if [[ "${STAGE4_2R3C3_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c3_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3c3_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3_export_runtime
printf '[Stage4.2R3c3] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3] source_stage4_2r3b_run=%s\n' "${SOURCE_R3B}"
printf '[Stage4.2R3c3] source_stage4_2r3c_run=%s\n' "${SOURCE_R3C}"
printf '[Stage4.2R3c3] source_stage4_2r3c1_run=%s\n' "${SOURCE_R3C1}"
printf '[Stage4.2R3c3] source_stage4_2r3c2_run=%s\n' "${SOURCE_R3C2}"
printf '[Stage4.2R3c3] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3c3] config=%s\n' "${STAGE4_2R3C3_CONFIG}"
printf '[Stage4.2R3c3] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3C3_COMMAND}" "${STAGE4_2R3C3_BACKEND}" \
  "${STAGE4_2R3C3_RESUME}" "${STAGE4_2R3C3_WORKERS}"
printf '[Stage4.2R3c3] Offline gate requires exact R3c1 baseline first actions in all 32 restart contexts before real TSC.\n'
printf '[Stage4.2R3c3] The 256 bounded +/- probes are task-clock relative, exactly zero-net, and identification-only.\n'
printf '[Stage4.2R3c3] Source actions/results, pair/history labels, source/current wire currents and current-run future values are forbidden from the controller.\n'
printf '[Stage4.2R3c3] The exact locked R3b four-pair snapshots are a development set, not independent confirmation.\n'
printf '[Stage4.2R3c3] Full wire current remains post-action audit telemetry and is forbidden from phase selection/control.\n'
printf '[Stage4.2R3c3] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3c3] Formal tracking is recorded but is not the preregistered identification acceptance gate.\n'
printf '[Stage4.2R3c3] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3C3_COMMAND}"
  --backend "${STAGE4_2R3C3_BACKEND}"
)
[[ "${STAGE4_2R3C3_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3C3_PYTHON}" \
  scripts/stage4_2r3c3_restart_task_clock_local_response_identification.py "${args[@]}"
