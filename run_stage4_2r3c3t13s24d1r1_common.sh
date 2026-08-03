#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r1_shell_common.sh"
stage4_2r3c3t13s24d1r1_validate_common
SOURCE_S21_RUN="$(stage4_2r3c3t13s23_find_s21_run)"
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
SOURCE_S23R1="${PROJECT_DIR}/stage4_2r3c3t13s23r1_audits/stage4_2r3c3t13s23r1_amplitude_coded_preflight_20260803_101707"
SOURCE_S24="${PROJECT_DIR}/stage4_2r3c3t13s24_runs/stage4_2r3c3t13s24_sequential_transition_identification_20260803_111226_0c71836"
SOURCE_S24_STAGE="${SOURCE_S24}/stage4_2r3c3t13s24_sequential_transition_identification"
SOURCE_S24_FORENSICS="${SOURCE_S24_STAGE}/analysis/independent_training_sequence_forensics.json"
SOURCE_S24_LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24_training-sequence_20260803_121237.log"
SOURCE_D1="${PROJECT_DIR}/stage4_2r3c3t13s24d1_audits/stage4_2r3c3t13s24d1_contracted_amplitude_preflight_20260803_143246"
OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R1_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r1_new_output_dir)}"
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: S24D1R1 output path exists: ${OUTPUT_DIR}" >&2; exit 1; }
for path in "${SOURCE_S23R1}" "${SOURCE_S24}" "${SOURCE_S24_FORENSICS}" "${SOURCE_S24_LOG}" "${SOURCE_D1}"; do
  [[ -e "${path}" ]] || { echo "ERROR: required immutable source missing: ${path}" >&2; exit 1; }
done
stage4_2r3c3t13s24d1r1_export_runtime
printf '[Stage4.2R3c3T13S24D1R1] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T13S24D1R1] source_d1=%s\nsource_s24=%s\noutput=%s\n' "${SOURCE_D1}" "${SOURCE_S24}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T13S24D1R1] zero plant/controller/Ray/gotsc/TSC; fixed Decimal grid only.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R1_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search.py \
  --config "${STAGE4_2R3C3T13S24D1R1_CONFIG}" --design-document "${STAGE4_2R3C3T13S24D1R1_DESIGN}" \
  --source-d1-config "${STAGE4_2R3C3T13S24D1_CONFIG}" \
  --source-d1-implementation "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1_contracted_amplitude_preflight.py" \
  --source-d1-output "${SOURCE_D1}" \
  --source-s23r1-config "${STAGE4_2R3C3T13S23R1_CONFIG}" \
  --source-s23r1-implementation "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight.py" \
  --source-s23r1-output "${SOURCE_S23R1}" --source-s24-run "${SOURCE_S24}" \
  --source-s24-config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24_sequential_transition_identification_370ms.json" \
  --source-s24-implementation "${PROJECT_DIR}/tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24_sequential_transition_identification.py" \
  --source-s24-hotfix-config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24_semantics_preserving_runtime_hotfix_v1.json" \
  --source-s24-hotfix-audit-tool "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24_semantics_preserving_runtime_hotfix.py" \
  --source-s24-forensic-tool "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24_training_sequence_forensics.py" \
  --source-s24-forensics "${SOURCE_S24_FORENSICS}" --source-s24-log "${SOURCE_S24_LOG}" \
  --source-s21-config "${STAGE4_2R3C3T13S23_S21_CONFIG}" --source-s21-run "${SOURCE_S21_RUN}" \
  --source-stage42r3b-run "${SOURCE_R3B}" --source-stage42r3c3-run "${SOURCE_R3C3}" \
  --source-stage42r3c3-bank-dir "${SOURCE_BANK}" --source-stage42r3c3t1-run "${SOURCE_T1}" \
  --source-stage42r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" --source-stage42r3c3t3-controller-bank "${SOURCE_T3_BANK}" \
  --q1-run "${Q1_RUN}" --q2-run "${Q2_RUN}" --q1-audit "${Q1_AUDIT}" --q2-audit "${Q2_AUDIT}" \
  --r3b-server-audit "${R3B_AUDIT}" --r3b-snapshot-checks "${R3B_SNAPSHOTS}" --output "${OUTPUT_DIR}"
