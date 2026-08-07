#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r8_shell_common.sh"

PYTHON="${STAGE4_2R3C3T13S24D1R14R8R9_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE4_2R3C3T13S24D1R14R8R9_CONFIG:-${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit.json}"
COMMAND="${STAGE4_2R3C3T13S24D1R14R8R9_COMMAND:-primary}"
OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R8R9_OUTPUT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r9_runs}"
RUN_DIR="${STAGE4_2R3C3T13S24D1R14R8R9_RUN_DIR:-${OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit_$(date -u +%Y%m%d_%H%M%S)}"
R8R7_RUN="${STAGE4_2R3C3T13S24D1R14R8R9_R8R7_RUN:-${STAGE4_2R3C3T13S24D1R14R8R8_R8R7_RUN}}"
R8R8_RUN="${STAGE4_2R3C3T13S24D1R14R8R9_R8R8_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r8_runs/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core_20260807_dface45_v2}"

[[ "${PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]]
[[ -x "${PYTHON}" ]]
[[ -f "${CONFIG}" ]]
[[ -d "${R8R7_RUN}" ]]
[[ -d "${R8R8_RUN}" ]]
[[ "${COMMAND}" == primary || "${COMMAND}" == independent ]]

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

if [[ "${COMMAND}" == primary ]]; then
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
else
  [[ -f "${RUN_DIR}/stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit/analysis/primary_detailed.json" ]]
fi

mkdir -p "${RUN_DIR}"
stage4_2r3c3t13s24d1r14r8r8_export
cd "${PROJECT_DIR}"
printf '[R8R9] user=%s host=%s command=%s run_dir=%s zero_new_tsc=true\n' "$(id -un)" "$(hostname)" "${COMMAND}" "${RUN_DIR}"

args=(
  --config "${CONFIG}" --run-dir "${RUN_DIR}" --r8r7-run "${R8R7_RUN}" --r8r8-run "${R8R8_RUN}"
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

if [[ "${COMMAND}" == primary ]]; then
  exec "${PYTHON}" tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r9_measured_multipulse_authority_audit.py "${args[@]}"
fi
exec "${PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r9_independent_forensics.py "${args[@]}"
