#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r3_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r3_shell_common.sh"
stage4_2r3c3t13s24d1r14r3_validate_common

SOURCE_R2_RUN="$(stage4_2r3c3t13s24d1r14r3_source_r2)"
SOURCE_D1R13_RUN="$(stage4_2r3c3t13s24d1r14r2_find_source_d1r13)"
SOURCE_D1R11_RUN="$(stage4_2r3c3t13s24d1r13_find_source_d1r11)"
SOURCE_R1A_OUTPUT="$(stage4_2r3c3t13s24d1r14r2_find_source_r1a)"
SOURCE_R2_INDEPENDENT="${SOURCE_R2_RUN}/server_independent_forensics_v1.json"
SOURCE_POSTHOC="${SOURCE_R2_RUN}/posthoc_sign_split_diagnostic_v1.json"
SOURCE_LOG_ROOT="${PROJECT_DIR}/logs/nohup"
SOURCE_LOG_OFFLINE="${SOURCE_LOG_ROOT}/stage4_2r3c3t13s24d1r14r2_offline_20260804_ca2815a_v1.log"
SOURCE_LOG_REAL="${SOURCE_LOG_ROOT}/stage4_2r3c3t13s24d1r14r2_real_20260804_ca2815a_v1.log"
SOURCE_LOG_POST="${SOURCE_LOG_ROOT}/stage4_2r3c3t13s24d1r14r2_postprocess_20260804_ca2815a_v1.log"

for path in "${SOURCE_R2_RUN}" "${SOURCE_D1R13_RUN}" "${SOURCE_D1R11_RUN}" "${SOURCE_R1A_OUTPUT}"; do
  [[ -d "${path}" ]] || { echo "ERROR: immutable source directory missing: ${path}" >&2; exit 1; }
done
for path in "${SOURCE_R2_INDEPENDENT}" "${SOURCE_POSTHOC}" "${SOURCE_LOG_OFFLINE}" "${SOURCE_LOG_REAL}" "${SOURCE_LOG_POST}"; do
  [[ -f "${path}" ]] || { echo "ERROR: immutable source file missing: ${path}" >&2; exit 1; }
done

OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R14R3_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r3_new_output)}"
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: fresh D1R14R3 output already exists: ${OUTPUT_DIR}" >&2; exit 1; }
stage4_2r3c3t13s24d1r14r3_export_runtime
printf '[T13S24D1R14R3] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R14R3] source_r2=%s\noutput=%s\n' "${SOURCE_R2_RUN}" "${OUTPUT_DIR}"
printf '[T13S24D1R14R3] zero controller/plant/Ray/gotsc/TSC; 72 source raw are read in place.\n'
cd "${PROJECT_DIR}"
common_args=(
  --project "${PROJECT_DIR}"
  --config "${STAGE4_2R3C3T13S24D1R14R3_CONFIG}"
  --design-document "${STAGE4_2R3C3T13S24D1R14R3_DESIGN}"
  --source-r2-run "${SOURCE_R2_RUN}"
  --source-d1r13-run "${SOURCE_D1R13_RUN}"
  --source-d1r11-run "${SOURCE_D1R11_RUN}"
  --source-r1a-output "${SOURCE_R1A_OUTPUT}"
  --source-r2-independent-result "${SOURCE_R2_INDEPENDENT}"
  --source-posthoc "${SOURCE_POSTHOC}"
  --source-log "${SOURCE_LOG_OFFLINE}"
  --source-log "${SOURCE_LOG_REAL}"
  --source-log "${SOURCE_LOG_POST}"
)
"${STAGE4_2R3C3T13S24D1R14R3_PYTHON}" -m \
  tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility \
  "${common_args[@]}" --output "${OUTPUT_DIR}"
PRIMARY="${OUTPUT_DIR}/stage4_2r3c3t13s24d1r14r3_primary_v1.json"
[[ -f "${PRIMARY}" ]] || { echo "ERROR: primary D1R14R3 output missing" >&2; exit 1; }
"${STAGE4_2R3C3T13S24D1R14R3_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r3_independent_forensics.py \
  "${common_args[@]}" --primary "${PRIMARY}" \
  --output "${OUTPUT_DIR}/stage4_2r3c3t13s24d1r14r3_independent_v1.json"
printf '[T13S24D1R14R3] completed; no TSC task was created.\n'

