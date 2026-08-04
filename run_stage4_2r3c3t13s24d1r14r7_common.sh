#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r7_shell_common.sh"
stage4_2r3c3t13s24d1r14r7_validate_common
SOURCE_R2_RUN="$(stage4_2r3c3t13s24d1r14r7_source_r2)"
SOURCE_R4_RUN="$(stage4_2r3c3t13s24d1r14r7_source_r4)"
SOURCE_R6_RUN="$(stage4_2r3c3t13s24d1r14r7_source_r6)"
OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R14R7_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r7_new_output)}"
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: fresh R7 output exists: ${OUTPUT_DIR}" >&2; exit 1; }
stage4_2r3c3t13s24d1r14r7_export_runtime
printf '[T13S24D1R14R7] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R14R7] source_r2=%s\nsource_r4=%s\nsource_r6=%s\noutput=%s\n' "${SOURCE_R2_RUN}" "${SOURCE_R4_RUN}" "${SOURCE_R6_RUN}" "${OUTPUT_DIR}"
printf '[T13S24D1R14R7] zero controller/plant/Ray/gotsc/TSC; 320 source raw read in place.\n'
cd "${PROJECT_DIR}"
args=(
  --config "${STAGE4_2R3C3T13S24D1R14R7_CONFIG}"
  --design-document "${STAGE4_2R3C3T13S24D1R14R7_DESIGN}"
  --source-r2-run "${SOURCE_R2_RUN}"
  --source-r4-run "${SOURCE_R4_RUN}"
  --source-r6-run "${SOURCE_R6_RUN}"
)
"${STAGE4_2R3C3T13S24D1R14R7_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7_causal_response_model.py \
  --project "${PROJECT_DIR}" "${args[@]}" --output "${OUTPUT_DIR}"
"${STAGE4_2R3C3T13S24D1R14R7_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7_independent_forensics.py \
  "${args[@]}" --primary-output "${OUTPUT_DIR}" --output "${OUTPUT_DIR}/stage4_2r3c3t13s24d1r14r7_independent_v1.json"
printf '[T13S24D1R14R7] completed; no TSC task was created.\n'
