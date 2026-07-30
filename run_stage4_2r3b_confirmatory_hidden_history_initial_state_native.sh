#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3b_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3b_shell_common.sh"
stage4_2r3b_validate_common
SOURCE_R2="$(stage4_2r3b_find_source_r2)" || {
  echo "ERROR: no complete certified Stage4.2R2 source run found" >&2
  exit 1
}
CALIBRATION_R3A="$(stage4_2r3b_find_calibration_r3a)" || {
  echo "ERROR: exact completed Stage4.2R3a calibration run/audit not found" >&2
  exit 1
}
if [[ -n "${STAGE4_2R3B_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3B_RUN_DIR}"
else
  RUN_DIR="$(stage4_2r3b_new_run_dir)"
fi
if [[ "${STAGE4_2R3B_RESUME}" == "1" ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3b_state.json" ]] || {
    echo "ERROR: resume state missing: ${RUN_DIR}/stage4_2r3b_state.json" >&2
    exit 1
  }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || {
    echo "ERROR: fresh run directory is not empty: ${RUN_DIR}" >&2
    exit 1
  }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3b_export_runtime
printf '[Stage4.2R3b] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3b] source_stage4_2r2_run=%s\n' "${SOURCE_R2}"
printf '[Stage4.2R3b] calibration_stage4_2r3a_run=%s\n' "${CALIBRATION_R3A}"
printf '[Stage4.2R3b] run_dir=%s\n' "${RUN_DIR}"
printf '[Stage4.2R3b] config=%s\n' "${STAGE4_2R3B_CONFIG}"
printf '[Stage4.2R3b] command=%s backend=%s resume=%s workers=%s\n' \
  "${STAGE4_2R3B_COMMAND}" "${STAGE4_2R3B_BACKEND}" \
  "${STAGE4_2R3B_RESUME}" "${STAGE4_2R3B_WORKERS}"
printf '[Stage4.2R3b] A no-gotsc gate first reproduces the required frozen R17 policies exactly from a fresh step-zero controller.\n'
printf '[Stage4.2R3b] State generation is fixed at 72 new real-TSC rollouts: prefix 5/9, directions 1/2, amplitude 0.60/0.75/0.90, gap 2/3/4, settle 4, both orders.\n'
printf '[Stage4.2R3b] The exact failed R3a calibration inventory/forensics is a source fingerprint; no R3a snapshot is reused as an R3b result.\n'
printf '[Stage4.2R3b] Hidden separation is frozen at max >=0.25 A, vector RMS >=0.10 A and relative RMS >=0.05.\n'
printf '[Stage4.2R3b] Common prefixes are exact authenticated nominal delay-0/slew-1.0 R17 actions; their source and digest are resume gates.\n'
printf '[Stage4.2R3b] Pair selection uses only preregistered visible/hidden checkpoint metrics and never control outcomes.\n'
printf '[Stage4.2R3b] Every selected snapshot starts a fresh causal controller and fresh TSC process; wire currents are post-action audit telemetry only.\n'
printf '[Stage4.2R3b] Formal timing remains 250/350 ms for slew 1.0 and 270/370 ms for slew 0.9.\n'
printf '[Stage4.2R3b] Large raw results and snapshots remain server-side; only compact postprocessed evidence is transferred.\n'
printf '[Stage4.2R3b] BC, DAgger and residual RL remain forbidden.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3B_CONFIG}"
  --source-stage4-2r2-run "${SOURCE_R2}"
  --calibration-stage4-2r3a-run "${CALIBRATION_R3A}"
  --run-dir "${RUN_DIR}"
  --command "${STAGE4_2R3B_COMMAND}"
  --backend "${STAGE4_2R3B_BACKEND}"
)
[[ "${STAGE4_2R3B_RESUME}" == "1" ]] && args+=(--resume)
exec "${STAGE4_2R3B_PYTHON}" \
  scripts/stage4_2r3b_confirmatory_hidden_history_initial_state.py "${args[@]}"
