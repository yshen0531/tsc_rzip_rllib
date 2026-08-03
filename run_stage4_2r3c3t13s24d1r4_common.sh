#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r4_shell_common.sh"
stage4_2r3c3t13s24d1r4_validate_common
SOURCE_D1R2_RUN="$(stage4_2r3c3t13s24d1r4_source_d1r2_run)"
SOURCE_D1R3_OUTPUT="$(stage4_2r3c3t13s24d1r4_source_d1r3_output)"
SOURCE_D1R3_PRIMARY_LOG="$(stage4_2r3c3t13s24d1r4_source_d1r3_primary_log)"
SOURCE_D1R3_REPEAT_LOG="$(stage4_2r3c3t13s24d1r4_source_d1r3_repeat_log)"
SOURCE_D1R1="$(stage4_2r3c3t13s24d1r2_source_d1r1)"
SOURCE_D1R1_LOG="$(stage4_2r3c3t13s24d1r2_source_d1r1_log)"
SOURCE_S21_RUN="$(stage4_2r3c3t13s24_find_source_s21)"
SOURCE_S23R1_OUTPUT="$(stage4_2r3c3t13s24_find_source_s23r1)"
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
RUN_DIR="${STAGE4_2R3C3T13S24D1R4_RUN_DIR:-$(stage4_2r3c3t13s24d1r4_new_run_dir)}"
STATE_FILE="${RUN_DIR}/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel/stage_state.json"
if [[ "${STAGE4_2R3C3T13S24D1R4_COMMAND}" == offline || "${STAGE4_2R3C3T13S24D1R4_COMMAND}" == all ]] && [[ "${STAGE4_2R3C3T13S24D1R4_RESUME}" == 0 ]]; then
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]] || { echo "ERROR: fresh D1R4 run directory not empty" >&2; exit 1; }
else
  [[ -f "${STATE_FILE}" ]] || { echo "ERROR: frozen D1R4 state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r4_export_runtime
printf '[T13S24D1R4] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R4] run_dir=%s command=%s backend=%s resume=%s workers=%s\n' "${RUN_DIR}" "${STAGE4_2R3C3T13S24D1R4_COMMAND}" "${STAGE4_2R3C3T13S24D1R4_BACKEND}" "${STAGE4_2R3C3T13S24D1R4_RESUME}" "${STAGE4_2R3C3T13S24D1R4_WORKERS}"
printf '[T13S24D1R4] exact nine-case real-TSC split-return safety sentinel.\n'
printf '[T13S24D1R4] arrival by 250 ms and hold through 350 ms unchanged; formal result diagnostic only.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S24D1R4_CONFIG}"
  --source-d1r2-run "${SOURCE_D1R2_RUN}" --source-d1r3-output "${SOURCE_D1R3_OUTPUT}"
  --source-d1r3-primary-log "${SOURCE_D1R3_PRIMARY_LOG}" --source-d1r3-repeat-log "${SOURCE_D1R3_REPEAT_LOG}"
  --source-d1r1-output "${SOURCE_D1R1}" --source-d1r1-log "${SOURCE_D1R1_LOG}"
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
  --run-dir "${RUN_DIR}" --command "${STAGE4_2R3C3T13S24D1R4_COMMAND}" --backend "${STAGE4_2R3C3T13S24D1R4_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S24D1R4_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S24D1R4_PYTHON}" scripts/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel.py "${args[@]}"
