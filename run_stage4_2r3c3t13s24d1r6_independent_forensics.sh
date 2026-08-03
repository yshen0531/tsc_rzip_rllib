#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r6_shell_common.sh"
stage4_2r3c3t13s24d1r6_validate_common
SOURCE_D1R4_RUN="$(stage4_2r3c3t13s24d1r6_source_d1r4_run)"
SOURCE_D1R4_COMPLETE_LOG="$(stage4_2r3c3t13s24d1r6_source_d1r4_complete_log)"
SOURCE_D1R5_PRIMARY_OUTPUT="$(stage4_2r3c3t13s24d1r6_source_d1r5_primary_output)"
SOURCE_D1R5_REPEAT_OUTPUT="$(stage4_2r3c3t13s24d1r6_source_d1r5_repeat_output)"
SOURCE_D1R5_PRIMARY_LOG="$(stage4_2r3c3t13s24d1r6_source_d1r5_primary_log)"
SOURCE_D1R5_REPEAT_LOG="$(stage4_2r3c3t13s24d1r6_source_d1r5_repeat_log)"
SOURCE_D1R2_RUN="$(stage4_2r3c3t13s24d1r6_source_d1r2_run)"
SOURCE_D1R3_OUTPUT="$(stage4_2r3c3t13s24d1r6_source_d1r3_output)"
SOURCE_D1R3_PRIMARY_LOG="$(stage4_2r3c3t13s24d1r6_source_d1r3_primary_log)"
SOURCE_D1R3_REPEAT_LOG="$(stage4_2r3c3t13s24d1r6_source_d1r3_repeat_log)"
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
RUN_DIR="${STAGE4_2R3C3T13S24D1R6_RUN_DIR:-$(cat "${STAGE4_2R3C3T13S24D1R6_OUTPUT_ROOT}/latest_stage4_2r3c3t13s24d1r6_run.txt")}"
COMPLETE_LOG="${STAGE4_2R3C3T13S24D1R6_LOG_FILE:-$(cat "${PROJECT_DIR}/logs/nohup/latest_stage4_2r3c3t13s24d1r6.log")}"
OUTPUT="${RUN_DIR}/stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel/analysis/independent_server_forensics.json"
[[ -f "${RUN_DIR}/stage4_2r3c3t13s24d1r6_recursive_split_return_safety_sentinel/final_result.json" ]] || { echo "ERROR: D1R6 final result missing" >&2; exit 1; }
[[ -f "${COMPLETE_LOG}" ]] || { echo "ERROR: D1R6 complete log missing" >&2; exit 1; }
[[ ! -e "${OUTPUT}" ]] || { echo "ERROR: D1R6 independent output must be new" >&2; exit 1; }
stage4_2r3c3t13s24d1r6_export_runtime
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R6_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r6_independent_forensics.py \
  --config "${STAGE4_2R3C3T13S24D1R6_CONFIG}" \
  --source-d1r4-run "${SOURCE_D1R4_RUN}" --source-d1r4-complete-log "${SOURCE_D1R4_COMPLETE_LOG}" \
  --source-d1r5-primary-output "${SOURCE_D1R5_PRIMARY_OUTPUT}" --source-d1r5-repeat-output "${SOURCE_D1R5_REPEAT_OUTPUT}" \
  --source-d1r5-primary-log "${SOURCE_D1R5_PRIMARY_LOG}" --source-d1r5-repeat-log "${SOURCE_D1R5_REPEAT_LOG}" \
  --source-d1r2-run "${SOURCE_D1R2_RUN}" \
  --source-d1r3-output "${SOURCE_D1R3_OUTPUT}" --source-d1r3-primary-log "${SOURCE_D1R3_PRIMARY_LOG}" \
  --source-d1r3-repeat-log "${SOURCE_D1R3_REPEAT_LOG}" --source-d1r1-output "${SOURCE_D1R1}" \
  --source-d1r1-log "${SOURCE_D1R1_LOG}" --source-s21-run "${SOURCE_S21_RUN}" \
  --source-s23r1-output "${SOURCE_S23R1_OUTPUT}" --source-stage42r3b-run "${SOURCE_R3B}" \
  --source-stage42r3c3-run "${SOURCE_R3C3}" --source-stage42r3c3-bank-dir "${SOURCE_BANK}" \
  --source-stage42r3c3t1-run "${SOURCE_T1}" --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" \
  --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}" --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" \
  --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}" --r3b-server-audit "${R3B_AUDIT}" \
  --r3b-snapshot-checks "${R3B_SNAPSHOTS}" --run-dir "${RUN_DIR}" --complete-log "${COMPLETE_LOG}" --output "${OUTPUT}"
