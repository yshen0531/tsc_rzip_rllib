#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8_shell_common.sh"
stage4_2r3c3t13s24d1r14r8_validate
SOURCE_D1R11="$(stage4_2r3c3t13s24d1r14r8_source_d1r11)"
SOURCE_R2="$(stage4_2r3c3t13s24d1r14r7r2_source r2)"
SOURCE_R4="$(stage4_2r3c3t13s24d1r14r7r2_source r4)"
SOURCE_R6="$(stage4_2r3c3t13s24d1r14r7r2_source r6)"
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
Q1_RUN="$(stage4_2r3c3t13s21_q1_run)"; Q2_RUN="$(stage4_2r3c3t13s21_q2_run)"
Q1_AUDIT="$(stage4_2r3c3t13s21_q1_audit)"; Q2_AUDIT="$(stage4_2r3c3t13s21_q2_audit)"
R3B_AUDIT="$(stage4_2r3c3t13s21_r3b_audit)"; R3B_SNAPSHOTS="$(stage4_2r3c3t13s21_r3b_snapshot_checks)"
RUN_DIR="${STAGE4_2R3C3T13S24D1R14R8_RUN_DIR:-$(stage4_2r3c3t13s24d1r14r8_new_run_dir)}"
STATE_FILE="${RUN_DIR}/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification/stage_state.json"
if [[ "${STAGE4_2R3C3T13S24D1R14R8_COMMAND}" == offline ]]; then
  [[ "${STAGE4_2R3C3T13S24D1R14R8_RESUME}" == 0 ]]
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
else
  [[ -f "${STATE_FILE}" ]] || { echo "ERROR: R8 frozen state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r14r8_export
cd "${PROJECT_DIR}"
printf '[R8] user=%s host=%s command=%s run_dir=%s resume=%s workers=%s\n' "$(id -un)" "$(hostname)" "${STAGE4_2R3C3T13S24D1R14R8_COMMAND}" "${RUN_DIR}" "${STAGE4_2R3C3T13S24D1R14R8_RESUME}" "${STAGE4_2R3C3T13S24D1R14R8_WORKERS}"
printf '[R8] immutable formal timing 250/270 ms arrival and 350/370 ms hold; probe raw is never expert data.\n'
independent_kind=""
case "${STAGE4_2R3C3T13S24D1R14R8_COMMAND}" in
  training-raw-independent) independent_kind=training_raw ;;
  training-model-independent) independent_kind=training_model ;;
  calibration-raw-independent) independent_kind=calibration_raw ;;
  calibration-model-independent) independent_kind=calibration_model ;;
  holdout-raw-independent) independent_kind=holdout_raw ;;
  holdout-model-independent) independent_kind=holdout_model ;;
esac
if [[ -n "${independent_kind}" ]]; then
  exec "${STAGE4_2R3C3T13S24D1R14R8_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8_independent_forensics.py \
    --config "${STAGE4_2R3C3T13S24D1R14R8_CONFIG}" --run-dir "${RUN_DIR}" \
    --source-r2-run "${SOURCE_R2}" --source-r4-run "${SOURCE_R4}" --source-r6-run "${SOURCE_R6}" --audit-kind "${independent_kind}"
fi
args=(
  --config "${STAGE4_2R3C3T13S24D1R14R8_CONFIG}" --source-d1r11-run "${SOURCE_D1R11}"
  --source-r2-run "${SOURCE_R2}" --source-r4-run "${SOURCE_R4}" --source-r6-run "${SOURCE_R6}"
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-s24-run "${SOURCE_S24_RUN}" --source-d1r9-v1 "${SOURCE_D1R9_V1}" --source-d1r9-v2 "${SOURCE_D1R9_V2}"
  --source-d1r10-run "${SOURCE_D1R10_RUN}" --source-d1r10-audit "${SOURCE_D1R10_AUDIT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
  --run-dir "${RUN_DIR}" --command "${STAGE4_2R3C3T13S24D1R14R8_COMMAND}" --backend "${STAGE4_2R3C3T13S24D1R14R8_BACKEND}"
)
[[ "${STAGE4_2R3C3T13S24D1R14R8_RESUME}" == 1 ]] && args+=(--resume)
exec "${STAGE4_2R3C3T13S24D1R14R8_PYTHON}" scripts/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification.py "${args[@]}"
