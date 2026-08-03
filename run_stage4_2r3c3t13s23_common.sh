#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s23_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s23_shell_common.sh"
stage4_2r3c3t13s23_validate_common
SOURCE_S21_RUN="$(stage4_2r3c3t13s23_find_s21_run)"
SOURCE_S22_OUTPUT="$(stage4_2r3c3t13s23_find_s22_output)"
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
OUTPUT_DIR="${STAGE4_2R3C3T13S23_OUTPUT_DIR:-$(stage4_2r3c3t13s23_new_output_dir)}"
[[ ! -e "${OUTPUT_DIR}" ]] || {
  echo "ERROR: S23 output must be a new path: ${OUTPUT_DIR}" >&2
  exit 1
}
stage4_2r3c3t13s23_export_runtime
printf '[Stage4.2R3c3T13S23] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T13S23] source_s21_run=%s\nsource_s22_output=%s\noutput=%s\n' \
  "${SOURCE_S21_RUN}" "${SOURCE_S22_OUTPUT}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T13S23] read-only exact-Card15 schedule replay: zero plant/controller/snapshot execution.\n'
printf '[Stage4.2R3c3T13S23] Formal 250/270 ms arrival and 350/370 ms hold timing is unchanged.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S23_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s23_sequential_hadamard_lattice_preflight.py \
  --config "${STAGE4_2R3C3T13S23_CONFIG}" \
  --source-s21-config "${STAGE4_2R3C3T13S23_S21_CONFIG}" \
  --source-s21-run "${SOURCE_S21_RUN}" \
  --source-s22-output "${SOURCE_S22_OUTPUT}" \
  --source-stage42r3b-run "${SOURCE_R3B}" \
  --source-stage42r3c3-run "${SOURCE_R3C3}" \
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" \
  --source-stage42r3c3t1-run "${SOURCE_T1}" \
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" \
  --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}" \
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" \
  --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}" \
  --r3b-server-audit "${R3B_AUDIT}" \
  --r3b-snapshot-checks "${R3B_SNAPSHOTS}" \
  --output "${OUTPUT_DIR}"
