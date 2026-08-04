#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r11_shell_common.sh"
stage4_2r3c3t13s24d1r11_validate_common
SOURCE_S21_RUN="$(stage4_2r3c3t13s24d1r11_find_source_s21)"
SOURCE_S23R1_OUTPUT="$(stage4_2r3c3t13s24d1r11_find_source_s23r1)"
SOURCE_S24_RUN="$(stage4_2r3c3t13s24d1r11_find_source_s24)"
SOURCE_D1R9_V1="$(stage4_2r3c3t13s24d1r11_find_source_d1r9_v1)"
SOURCE_D1R9_V2="$(stage4_2r3c3t13s24d1r11_find_source_d1r9_v2)"
SOURCE_D1R10_RUN="$(stage4_2r3c3t13s24d1r11_find_source_d1r10)"
SOURCE_D1R10_AUDIT="$(stage4_2r3c3t13s24d1r11_find_source_d1r10_audit)"
SOURCE_R3B="$(stage4_2r3c3t13s21_find_source_r3b)"
SOURCE_R3C3="$(stage4_2r3c3t13s21_find_source_r3c3)"
SOURCE_BANK="$(stage4_2r3c3t13s21_find_source_bank)"
SOURCE_T1="$(stage4_2r3c3t13s21_find_source_t1)"
SOURCE_T1_AUDIT="$(stage4_2r3c3t13s21_find_source_t1_audit)"
SOURCE_T3_BANK="$(stage4_2r3c3t13s21_find_t3_controller_bank)"
Q1_RUN="$(stage4_2r3c3t13s21_q1_run)"
Q2_RUN="$(stage4_2r3c3t13s21_q2_run)"
Q1_AUDIT="$(stage4_2r3c3t13s21_q1_audit)"
Q2_AUDIT="$(stage4_2r3c3t13s21_q2_audit)"
R3B_AUDIT="$(stage4_2r3c3t13s21_r3b_audit)"
R3B_SNAPSHOTS="$(stage4_2r3c3t13s21_r3b_snapshot_checks)"
for path in "${SOURCE_S21_RUN}" "${SOURCE_S23R1_OUTPUT}" "${SOURCE_S24_RUN}" "${SOURCE_D1R9_V1}" "${SOURCE_D1R9_V2}" "${SOURCE_D1R10_RUN}" "${SOURCE_R3B}" "${SOURCE_R3C3}" "${SOURCE_BANK}" "${SOURCE_T1}" "${SOURCE_T1_AUDIT}" "${Q1_RUN}" "${Q2_RUN}"; do
  [[ -d "${path}" ]] || { echo "ERROR: source directory missing: ${path}" >&2; exit 1; }
done
for path in "${SOURCE_D1R10_AUDIT}" "${SOURCE_T3_BANK}" "${Q1_AUDIT}" "${Q2_AUDIT}" "${R3B_AUDIT}" "${R3B_SNAPSHOTS}"; do
  [[ -f "${path}" ]] || { echo "ERROR: source audit missing: ${path}" >&2; exit 1; }
done
RUN_DIR="${STAGE4_2R3C3T13S24D1R11_RUN_DIR:-$(stage4_2r3c3t13s24d1r11_new_run_dir)}"
STATE_FILE="${RUN_DIR}/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification/stage_state.json"
if [[ "${STAGE4_2R3C3T13S24D1R11_COMMAND}" == offline ]]; then
  [[ "${STAGE4_2R3C3T13S24D1R11_RESUME}" == 0 ]] || { echo "ERROR: offline phase cannot resume" >&2; exit 1; }
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory not empty" >&2; exit 1; }
else
  [[ -f "${STATE_FILE}" ]] || { echo "ERROR: S24D1R11 frozen state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r11_export_runtime
printf '[T13S24D1R11] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R11] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' "${RUN_DIR}" "${STAGE4_2R3C3T13S24D1R11_COMMAND}" "${STAGE4_2R3C3T13S24D1R11_BACKEND}" "${STAGE4_2R3C3T13S24D1R11_RESUME}" "${STAGE4_2R3C3T13S24D1R11_WORKERS}"
printf '[T13S24D1R11] frozen phased matrix: training 600, calibration 200, holdout 200; total 1000.\n'
printf '[T13S24D1R11] formal 250/270 ms arrival and 350/370 ms hold timing is unchanged.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S24D1R11_CONFIG}" --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-s24-run "${SOURCE_S24_RUN}" --source-d1r9-v1 "${SOURCE_D1R9_V1}" --source-d1r9-v2 "${SOURCE_D1R9_V2}"
  --source-d1r10-run "${SOURCE_D1R10_RUN}" --source-d1r10-audit "${SOURCE_D1R10_AUDIT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
  --run-dir "${RUN_DIR}" --command "${STAGE4_2R3C3T13S24D1R11_COMMAND}" --backend "${STAGE4_2R3C3T13S24D1R11_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S24D1R11_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S24D1R11_PYTHON}" scripts/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification.py "${args[@]}"
