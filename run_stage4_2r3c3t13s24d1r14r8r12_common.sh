#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${STAGE4_2R3C3T13S24D1R14R8R12_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
CONFIG="${STAGE4_2R3C3T13S24D1R14R8R12_CONFIG:-${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_370ms.json}"
COMMAND="${STAGE4_2R3C3T13S24D1R14R8R12_COMMAND:-offline}"
BACKEND="${STAGE4_2R3C3T13S24D1R14R8R12_BACKEND:-ray}"
RESUME="${STAGE4_2R3C3T13S24D1R14R8R12_RESUME:-0}"
OUTPUT_ROOT="${STAGE4_2R3C3T13S24D1R14R8R12_OUTPUT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r12_runs}"
R8R7_RUN="${STAGE4_2R3C3T13S24D1R14R8R12_R8R7_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r7_runs/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel_20260807_d8d231e_v1}"
R8R11_RUN="${STAGE4_2R3C3T13S24D1R14R8R12_R8R11_RUN:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r8r11_runs/stage4_2r3c3t13s24d1r14r8r11_sustained_exact_target_refresh_authority_sentinel_20260807_863692b_v1}"
RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_2r3c3t13s24d1r14r8r12_${UID:-0}}"

STAGE4_2R3C3T13S24D1R14R8R7_PROJECT_DIR="${PROJECT_DIR}"
STAGE4_2R3C3T13S24D1R14R8R7_PYTHON="${PYTHON}"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r7_shell_common.sh"

[[ "${PROJECT_DIR}" == "/home/yangshen0711/tsc_all/tsc_rzip_rllib" ]]
[[ -x "${PYTHON}" ]]
[[ -f "${CONFIG}" ]]
[[ -d "${R8R7_RUN}" ]]
[[ -d "${R8R11_RUN}" ]]
[[ "${BACKEND}" == ray || "${BACKEND}" == serial ]]
[[ "${RESUME}" == 0 || "${RESUME}" == 1 ]]
case "${COMMAND}" in
  offline|offline-independent|authorize-safety|safety|safety-raw-independent|authorize-qualification|qualification|qualification-raw-independent|finalize-primary|final-independent|postprocess) ;;
  *) echo "ERROR: unsupported R8R12 command ${COMMAND}" >&2; exit 1 ;;
esac

SOURCE_D1R11="$(stage4_2r3c3t13s24d1r14r8_source_d1r11)"
SOURCE_R2="$(stage4_2r3c3t13s24d1r14r7r2_source r2)"
SOURCE_R4="$(stage4_2r3c3t13s24d1r14r7r2_source r4)"
SOURCE_R6="$(stage4_2r3c3t13s24d1r14r7r2_source r6)"
SOURCE_S21_RUN="$(stage4_2r3c3t13s21_find_source_s21)"
SOURCE_S23R1_OUTPUT="$(stage4_2r3c3t13s21_find_source_s23r1)"
SOURCE_S24_RUN="$(stage4_2r3c3t13s21_find_source_s24)"
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

if [[ -n "${STAGE4_2R3C3T13S24D1R14R8R12_RUN_DIR:-}" ]]; then
  RUN_DIR="${STAGE4_2R3C3T13S24D1R14R8R12_RUN_DIR}"
else
  mkdir -p "${OUTPUT_ROOT}"
  RUN_DIR="${OUTPUT_ROOT}/stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel_$(date -u +%Y%m%d_%H%M%S)"
fi
STAGE_DIR="${RUN_DIR}/stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel"
if [[ "${COMMAND}" == offline ]]; then
  [[ ! -e "${RUN_DIR}" || -z "$(find "${RUN_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]
else
  [[ -f "${STAGE_DIR}/stage_state.json" ]] || { echo "ERROR: R8R12 frozen state missing" >&2; exit 1; }
fi
mkdir -p "${RUN_DIR}"

export PROJECT_DIR PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" RAY_TMPDIR
STAGE4_2R3C3T13S24D1R14R8_TSC_WORKSPACE_ROOT="${STAGE4_2R3C3T13S24D1R14R8_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
STAGE4_2R3C3T13S24D1R14R8_TSC_RUN_ROOT="${STAGE4_2R3C3T13S24D1R14R8_TSC_RUN_ROOT:-${STAGE4_2R3C3T13S24D1R14R8_TSC_WORKSPACE_ROOT}/episode_runs}"
stage4_2r3c3t13s24d1r14r8r7_export
cd "${PROJECT_DIR}"
printf '[R8R12] user=%s host=%s command=%s run_dir=%s\n' "$(id -un)" "$(hostname)" "${COMMAND}" "${RUN_DIR}"
printf '[R8R12] maximum 16 fresh safety/qualification trajectories; all are forbidden from expert and learning data.\n'

args=(
  --config "${CONFIG}" --run-dir "${RUN_DIR}" --r8r7-run "${R8R7_RUN}" --r8r11-run "${R8R11_RUN}"
  --r8-run "${STAGE4_2R3C3T13S24D1R14R8R7_R8_RUN}" --r8r1-output "${STAGE4_2R3C3T13S24D1R14R8R7_R8R1_OUTPUT}" --r8r6-run "${STAGE4_2R3C3T13S24D1R14R8R7_R8R6_RUN}"
  --source-d1r11-run "${SOURCE_D1R11}" --source-r2-run "${SOURCE_R2}" --source-r4-run "${SOURCE_R4}" --source-r6-run "${SOURCE_R6}"
  --source-s21-run "${SOURCE_S21_RUN}" --source-s23r1-output "${SOURCE_S23R1_OUTPUT}" --source-s24-run "${SOURCE_S24_RUN}"
  --source-d1r9-v1 "${SOURCE_D1R9_V1}" --source-d1r9-v2 "${SOURCE_D1R9_V2}" --source-d1r10-run "${SOURCE_D1R10_RUN}" --source-d1r10-audit "${SOURCE_D1R10_AUDIT}"
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}" --source-stage42r3c3-bank-dir "${SOURCE_BANK}"
  --source-stage42r3c3t1-run "${SOURCE_T1}" --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}"
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}"
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}"
)

case "${COMMAND}" in
  offline-independent) AUDIT_KIND=offline ;;
  safety-raw-independent) AUDIT_KIND=safety_raw ;;
  qualification-raw-independent) AUDIT_KIND=qualification_raw ;;
  final-independent) AUDIT_KIND=final ;;
  *) AUDIT_KIND= ;;
esac
if [[ -n "${AUDIT_KIND}" ]]; then
  exec "${PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r12_independent_forensics.py "${args[@]}" --audit-kind "${AUDIT_KIND}"
fi
if [[ "${RESUME}" == 1 ]]; then args+=(--resume); fi
exec "${PYTHON}" -m tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r12_causal_cumulative_direction2_staircase_authority_sentinel "${args[@]}" --command "${COMMAND}" --backend "${BACKEND}"
