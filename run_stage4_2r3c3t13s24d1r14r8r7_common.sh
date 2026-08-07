#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r7_shell_common.sh"
stage4_2r3c3t13s24d1r14r8r7_validate
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
RUN_DIR="${STAGE4_2R3C3T13S24D1R14R8R7_RUN_DIR:-$(stage4_2r3c3t13s24d1r14r8r7_new_run_dir)}"
STATE_FILE="${RUN_DIR}/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel/stage_state.json"
if [[ "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" == offline ]]; then
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
elif [[ "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" != self-test ]]; then
  [[ -f "${STATE_FILE}" ]] || { echo "ERROR: R8R7 frozen state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r14r8r7_export
cd "${PROJECT_DIR}"
printf '[R8R7] user=%s host=%s command=%s run_dir=%s\n' "$(id -un)" "$(hostname)" "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" "${RUN_DIR}"
printf '[R8R7] conditional maximum 48 fresh sentinel trajectories; all are forbidden from expert and learning data.\n'
if [[ "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" == self-test ]]; then
  exec "${STAGE4_2R3C3T13S24D1R14R8R7_PYTHON}" -c "from pathlib import Path; from tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel import self_test; print(self_test(Path(r'${STAGE4_2R3C3T13S24D1R14R8R7_CONFIG}')))"
fi
args=(
  --config "${STAGE4_2R3C3T13S24D1R14R8R7_CONFIG}" --run-dir "${RUN_DIR}"
  --r8-run "${STAGE4_2R3C3T13S24D1R14R8R7_R8_RUN}" --r8r1-output "${STAGE4_2R3C3T13S24D1R14R8R7_R8R1_OUTPUT}" --r8r6-run "${STAGE4_2R3C3T13S24D1R14R8R7_R8R6_RUN}"
  --source-d1r11-run "${SOURCE_D1R11}" --source-r2-run "${SOURCE_R2}" --source-r4-run "${SOURCE_R4}" --source-r6-run "${SOURCE_R6}"
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}"
  --source-s24-run "${SOURCE_S24_RUN}" --source-d1r9-v1 "${SOURCE_D1R9_V1}" --source-d1r9-v2 "${SOURCE_D1R9_V2}"
  --source-d1r10-run "${SOURCE_D1R10_RUN}" --source-d1r10-audit "${SOURCE_D1R10_AUDIT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}"
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}"
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
)
case "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" in
  offline-independent) AUDIT_KIND=offline ;;
  baseline-raw-independent) AUDIT_KIND=baseline_raw ;;
  baseline-model-independent) AUDIT_KIND=baseline_model ;;
  multipulse-raw-independent) AUDIT_KIND=multipulse_raw ;;
  multipulse-model-independent) AUDIT_KIND=multipulse_model ;;
  *) AUDIT_KIND= ;;
esac
if [[ -n "${AUDIT_KIND}" ]]; then
  exec "${STAGE4_2R3C3T13S24D1R14R8R7_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r7_independent_forensics.py "${args[@]}" --command offline --audit-kind "${AUDIT_KIND}"
fi
if [[ "${STAGE4_2R3C3T13S24D1R14R8R7_RESUME}" == 1 ]]; then args+=(--resume); fi
exec "${STAGE4_2R3C3T13S24D1R14R8R7_PYTHON}" scripts/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign.py "${args[@]}" --command "${STAGE4_2R3C3T13S24D1R14R8R7_COMMAND}" --backend "${STAGE4_2R3C3T13S24D1R14R8R7_BACKEND}"
