#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r4_shell_common.sh"
stage4_2r3c3t13s24d1r14r4_validate_common
SOURCE_D1R13_RUN="$(stage4_2r3c3t13s24d1r14r4_find_source_d1r13)"
SOURCE_D1R13_AUDIT="$(stage4_2r3c3t13s24d1r14r4_find_source_d1r13_audit)"
SOURCE_R1A_OUTPUT="$(stage4_2r3c3t13s24d1r14r4_find_source_r1a)"
SOURCE_R2_RUN="$(stage4_2r3c3t13s24d1r14r4_find_source_r2)"
SOURCE_R3_INITIAL_OUTPUT="$(stage4_2r3c3t13s24d1r14r4_find_source_r3_initial)"
SOURCE_R3_CORRECTED_OUTPUT="$(stage4_2r3c3t13s24d1r14r4_find_source_r3_corrected)"
SOURCE_D1R11_RUN="$(stage4_2r3c3t13s24d1r13_find_source_d1r11)"
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
for path in "${SOURCE_R1A_OUTPUT}" "${SOURCE_R2_RUN}" "${SOURCE_R3_INITIAL_OUTPUT}" "${SOURCE_R3_CORRECTED_OUTPUT}" "${SOURCE_D1R13_RUN}" "${SOURCE_D1R11_RUN}" "${SOURCE_S21_RUN}" "${SOURCE_S23R1_OUTPUT}" "${SOURCE_S24_RUN}" "${SOURCE_D1R9_V1}" "${SOURCE_D1R9_V2}" "${SOURCE_D1R10_RUN}" "${SOURCE_R3B}" "${SOURCE_R3C3}" "${SOURCE_BANK}" "${SOURCE_T1}" "${SOURCE_T1_AUDIT}" "${Q1_RUN}" "${Q2_RUN}"; do
  [[ -d "${path}" ]] || { echo "ERROR: source directory missing: ${path}" >&2; exit 1; }
done
for path in "${SOURCE_D1R13_AUDIT}" "${SOURCE_D1R10_AUDIT}" "${SOURCE_T3_BANK}" "${Q1_AUDIT}" "${Q2_AUDIT}" "${R3B_AUDIT}" "${R3B_SNAPSHOTS}"; do
  [[ -f "${path}" ]] || { echo "ERROR: source audit missing: ${path}" >&2; exit 1; }
done
RUN_DIR="${STAGE4_2R3C3T13S24D1R14R4_RUN_DIR:-$(stage4_2r3c3t13s24d1r14r4_new_run_dir)}"
STATE_FILE="${RUN_DIR}/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel/stage_state.json"
if [[ "${STAGE4_2R3C3T13S24D1R14R4_COMMAND}" == offline ]]; then
  [[ "${STAGE4_2R3C3T13S24D1R14R4_RESUME}" == 0 ]] || { echo "ERROR: offline phase cannot resume" >&2; exit 1; }
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh run directory not empty" >&2; exit 1; }
else
  [[ -f "${STATE_FILE}" ]] || { echo "ERROR: D1R14R4 frozen state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r14r4_export_runtime
printf '[T13S24D1R14R4] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R14R4] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' "${RUN_DIR}" "${STAGE4_2R3C3T13S24D1R14R4_COMMAND}" "${STAGE4_2R3C3T13S24D1R14R4_BACKEND}" "${STAGE4_2R3C3T13S24D1R14R4_RESUME}" "${STAGE4_2R3C3T13S24D1R14R4_WORKERS}"
printf '[T13S24D1R14R4] 200 fresh TSC time-shifted sign-split sentinels; formal tracking is diagnostic only.\n'
printf '[T13S24D1R14R4] formal 250/270 ms arrival and 350/370 ms hold timing is unchanged.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S24D1R14R4_CONFIG}" --source-d1r13-run "${SOURCE_D1R13_RUN}" --source-d1r13-audit "${SOURCE_D1R13_AUDIT}" --source-r1a-output "${SOURCE_R1A_OUTPUT}"
  --source-r2-run "${SOURCE_R2_RUN}" --source-r3-initial-output "${SOURCE_R3_INITIAL_OUTPUT}" --source-r3-corrected-output "${SOURCE_R3_CORRECTED_OUTPUT}"
  --source-d1r11-run "${SOURCE_D1R11_RUN}" --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-s24-run "${SOURCE_S24_RUN}" --source-d1r9-v1 "${SOURCE_D1R9_V1}" --source-d1r9-v2 "${SOURCE_D1R9_V2}"
  --source-d1r10-run "${SOURCE_D1R10_RUN}" --source-d1r10-audit "${SOURCE_D1R10_AUDIT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
  --run-dir "${RUN_DIR}" --command "${STAGE4_2R3C3T13S24D1R14R4_COMMAND}" --backend "${STAGE4_2R3C3T13S24D1R14R4_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S24D1R14R4_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S24D1R14R4_PYTHON}" scripts/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel.py "${args[@]}"
