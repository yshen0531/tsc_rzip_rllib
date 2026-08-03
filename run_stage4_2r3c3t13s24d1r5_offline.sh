#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R5_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python missing" >&2; exit 1; }

# shellcheck source=scripts/stage4_2r3c3t13s24d1r4_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r4_shell_common.sh"
STAGE4_2R3C3T13S24D1R4_PROJECT_DIR="${PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R4_PYTHON="${PYTHON_BIN}"
STAGE4_2R3C3T13S24D1R4_WORKERS=9
STAGE4_2R3C3T13S24D1R4_BACKEND=serial
STAGE4_2R3C3T13S24D1R4_COMMAND=postprocess
STAGE4_2R3C3T13S24D1R4_RESUME=1
stage4_2r3c3t13s24d1r4_validate_common
stage4_2r3c3t13s24d1r4_export_runtime

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

D1R4_RUN="${PROJECT_DIR}/stage4_2r3c3t13s24d1r4_runs/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_20260803_1802_da3f4b4_v1h2"
COMPLETE_LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r4_real_20260803_1804_da3f4b4_v1h2.log"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTPUT="${STAGE4_2R3C3T13S24D1R5_OUTPUT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r5_audits/stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_${STAMP}}"
[[ ! -e "${OUTPUT}" ]] || { echo "ERROR: D1R5 output must be new" >&2; exit 1; }
[[ -f "${COMPLETE_LOG}" ]] || { echo "ERROR: frozen D1R4 complete log missing" >&2; exit 1; }

COMMON_ARGS=(
  --config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r5_recursive_split_return_preflight_v1.json"
  --source-d1r4-config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r4_causal_split_return_safety_sentinel_350ms.json"
  --source-d1r4-run "${D1R4_RUN}" --complete-log "${COMPLETE_LOG}" --output "${OUTPUT}"
  --source-d1r2-run "${SOURCE_D1R2_RUN}" --source-d1r3-output "${SOURCE_D1R3_OUTPUT}"
  --source-d1r3-primary-log "${SOURCE_D1R3_PRIMARY_LOG}" --source-d1r3-repeat-log "${SOURCE_D1R3_REPEAT_LOG}"
  --source-d1r1-output "${SOURCE_D1R1}" --source-d1r1-log "${SOURCE_D1R1_LOG}"
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
)

printf '[T13S24D1R5] zero-new-TSC recursive replay; output=%s\n' "${OUTPUT}"
"${PYTHON_BIN}" \
  "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r5_recursive_split_return_preflight.py" \
  "${COMMON_ARGS[@]}"
"${PYTHON_BIN}" \
  "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r5_independent_forensics.py" \
  "${COMMON_ARGS[@]}"
printf '[T13S24D1R5] primary and independent audit complete; zero plant steps\n'
