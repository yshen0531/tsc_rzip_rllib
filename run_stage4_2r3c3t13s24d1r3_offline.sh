#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python missing" >&2; exit 1; }
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r2_shell_common.sh"
STAGE4_2R3C3T13S24D1R2_PROJECT_DIR="${PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R2_PYTHON="${PYTHON_BIN}"
STAGE4_2R3C3T13S24D1R2_WORKERS=54
STAGE4_2R3C3T13S24D1R2_BACKEND=serial
STAGE4_2R3C3T13S24D1R2_COMMAND=postprocess
STAGE4_2R3C3T13S24D1R2_RESUME=1
stage4_2r3c3t13s24d1r2_validate_common
stage4_2r3c3t13s24d1r2_export_runtime
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
D1R2_RUN="${PROJECT_DIR}/stage4_2r3c3t13s24d1r2_runs/stage4_2r3c3t13s24d1r2_geometry_restored_amplitude_safety_sentinel_20260803_160327_9e6bba2_v2"
COMPLETE_LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r2_rollout_20260803_160426_9e6bba2_v2.log"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTPUT="${STAGE4_2R3C3T13S24D1R3_OUTPUT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r3_audits/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_${STAMP}}"
[[ ! -e "${OUTPUT}" ]] || { echo "ERROR: D1R3 output must be new" >&2; exit 1; }
printf '[T13S24D1R3] zero-new-TSC causal replay; output=%s\n' "${OUTPUT}"
exec "${PYTHON_BIN}" \
  "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r3_causal_split_return_preflight.py" \
  --config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r3_causal_split_return_preflight_v1.json" \
  --source-d1r2-config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel_370ms.json" \
  --source-d1r2-run "${D1R2_RUN}" --complete-log "${COMPLETE_LOG}" --output "${OUTPUT}" \
  --source-d1r1-output "${SOURCE_D1R1}" --source-d1r1-log "${SOURCE_D1R1_LOG}" \
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}" \
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}" \
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}" \
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}" \
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}" \
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
