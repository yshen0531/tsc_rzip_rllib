#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s14_shell_common.sh"
stage4_2r3c3t13s14_validate_common
SOURCE_R3B="$(stage4_2r3c3t13s14_find_source_r3b)"
SOURCE_R3C3="$(stage4_2r3c3t13s14_find_source_r3c3)"
SOURCE_BANK="$(stage4_2r3c3t13s14_find_source_bank)"
SOURCE_T1="$(stage4_2r3c3t13s14_find_source_t1)"
SOURCE_T1_AUDIT="$(stage4_2r3c3t13s14_find_source_t1_audit)"
SOURCE_T3_BANK="$(stage4_2r3c3t13s14_find_t3_controller_bank)"
Q1_RUN="$(stage4_2r3c3t13s14_q1_run)"
Q2_RUN="$(stage4_2r3c3t13s14_q2_run)"
Q1_AUDIT="$(stage4_2r3c3t13s14_q1_audit)"
Q2_AUDIT="$(stage4_2r3c3t13s14_q2_audit)"
R3B_AUDIT="$(stage4_2r3c3t13s14_r3b_audit)"
R3B_SNAPSHOTS="$(stage4_2r3c3t13s14_r3b_snapshot_checks)"
for path in "${SOURCE_R3B}" "${SOURCE_R3C3}" "${SOURCE_BANK}" "${SOURCE_T1}" "${SOURCE_T1_AUDIT}" "${Q1_RUN}" "${Q2_RUN}"; do
  [[ -d "${path}" ]] || { echo "ERROR: source directory missing: ${path}" >&2; exit 1; }
done
for path in "${SOURCE_T3_BANK}" "${Q1_AUDIT}" "${Q2_AUDIT}" "${R3B_AUDIT}" "${R3B_SNAPSHOTS}"; do
  [[ -f "${path}" ]] || { echo "ERROR: source audit missing: ${path}" >&2; exit 1; }
done
RUN_DIR="${STAGE4_2R3C3T13S14_RUN_DIR:-$(stage4_2r3c3t13s14_new_run_dir)}"
if [[ "${STAGE4_2R3C3T13S14_RESUME}" == 1 ]]; then
  [[ -f "${RUN_DIR}/stage4_2r3c3t13s14_state.json" ]] || { echo "ERROR: resume state missing" >&2; exit 1; }
else
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory not empty" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s14_export_runtime
printf '[T13S14] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S14] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' "${RUN_DIR}" "${STAGE4_2R3C3T13S14_COMMAND}" "${STAGE4_2R3C3T13S14_BACKEND}" "${STAGE4_2R3C3T13S14_RESUME}" "${STAGE4_2R3C3T13S14_WORKERS}"
printf '[T13S14] 16 calibrated baselines + 128 signed responses = 144 real trajectories.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S14_CONFIG}"
  --source-stage4-2r3b-run "${SOURCE_R3B}"
  --source-stage4-2r3c3-run "${SOURCE_R3C3}"
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}"
  --source-stage4-2r3c3t1-run "${SOURCE_T1}"
  --source-stage4-2r3c3t1-audit-dir "${SOURCE_T1_AUDIT}"
  --source-stage4-2r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}"
  --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
  --run-dir "${RUN_DIR}" --command "${STAGE4_2R3C3T13S14_COMMAND}" --backend "${STAGE4_2R3C3T13S14_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S14_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S14_PYTHON}" scripts/stage4_2r3c3t13s14_active_calibration_sentinel.py "${args[@]}"
