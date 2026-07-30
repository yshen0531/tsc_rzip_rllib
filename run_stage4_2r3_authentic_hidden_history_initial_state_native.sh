#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3_shell_common.sh"
stage4_2r3_validate_common
SOURCE_R2="$(stage4_2r3_find_source_r2)" || {
  echo "ERROR: no complete certified Stage4.2R2 source run found" >&2
  exit 1
}
if [[ -n "${STAGE4_2R3_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3_new_run_dir)"
fi
if [[ "${STAGE4_2R3_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3_export_runtime
printf '[Stage4.2R3] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3] source_stage4_2r2_run=%s\n' "${SOURCE_R2}"
printf '[Stage4.2R3] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3] config=%s\n' "${STAGE4_2R3_CONFIG}"
printf '[Stage4.2R3] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3_COMMAND}" "${STAGE4_2R3_BACKEND}" \
  "${STAGE4_2R3_RESUME}" "${STAGE4_2R3_WORKERS}"
printf '[Stage4.2R3] A no-gotsc gate first reproduces the required frozen R17 policies exactly from a fresh step-zero controller.\n'
printf '[Stage4.2R3] Pair selection uses only preregistered visible/hidden checkpoint metrics and never control outcomes.\n'
printf '[Stage4.2R3] Every selected snapshot starts a fresh causal controller and fresh TSC process; wire currents are post-action audit telemetry only.\n'
printf '[Stage4.2R3] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3] Large raw results and snapshots remain server-side; only compact postprocessed evidence is transferred.\n'
printf '[Stage4.2R3] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3_CONFIG}"
  --source-stage4-2r2-run "${SOURCE_R2}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3_COMMAND}"
  --backend "${STAGE4_2R3_BACKEND}"
)
[[ "${STAGE4_2R3_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3_PYTHON}" \
  scripts/stage4_2r3_authentic_hidden_history_initial_state.py "${args[@]}"
