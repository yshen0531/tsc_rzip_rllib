#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3a_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3a_shell_common.sh"
stage4_2r3a_validate_common
SOURCE_R2="$(stage4_2r3a_find_source_r2)" || {
  echo "ERROR: no complete certified Stage4.2R2 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_2R3A_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3A_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3a_new_run_dir)"
fi
if [[ "${STAGE4_2R3A_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3a_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3a_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3a_export_runtime
printf '[Stage4.2R3a] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3a] source_stage4_2r2_run=%s\n' "${SOURCE_R2}"
printf '[Stage4.2R3a] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3a] config=%s\n' "${STAGE4_2R3A_CONFIG}"
printf '[Stage4.2R3a] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3A_COMMAND}" "${STAGE4_2R3A_BACKEND}" \
  "${STAGE4_2R3A_RESUME}" "${STAGE4_2R3A_WORKERS}"
printf '[Stage4.2R3a] A no-gotsc gate first reproduces the required frozen R17 policies exactly from a fresh step-zero controller.\n'
printf '[Stage4.2R3a] State generation is fixed at 72 real-TSC rollouts: prefix 4/8, directions 1/2, amplitude 0.2/0.4/0.8, gap 2/4/8, settle 4, both orders.\n'
printf '[Stage4.2R3a] Common prefixes are exact authenticated nominal delay-0/slew-1.0 R17 actions; their source and digest are resume gates.\n'
printf '[Stage4.2R3a] Pair selection uses only preregistered visible/hidden checkpoint metrics and never control outcomes.\n'
printf '[Stage4.2R3a] Every selected snapshot starts a fresh causal controller and fresh TSC process; wire currents are post-action audit telemetry only.\n'
printf '[Stage4.2R3a] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3a] Large raw results and snapshots remain server-side; only compact postprocessed evidence is transferred.\n'
printf '[Stage4.2R3a] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3A_CONFIG}"
  --source-stage4-2r2-run "${SOURCE_R2}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3A_COMMAND}"
  --backend "${STAGE4_2R3A_BACKEND}"
)
[[ "${STAGE4_2R3A_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3A_PYTHON}" \
  scripts/stage4_2r3a_delayed_counterpulse_hidden_history_initial_state.py "${args[@]}"
