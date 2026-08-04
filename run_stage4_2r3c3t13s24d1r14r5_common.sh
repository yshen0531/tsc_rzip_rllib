#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r5_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r5_shell_common.sh"
stage4_2r3c3t13s24d1r14r5_validate_common

SOURCE_R4_RUN="$(stage4_2r3c3t13s24d1r14r5_source_r4)"
SOURCE_R2_RUN="$(stage4_2r3c3t13s24d1r14r5_source_r2)"
SOURCE_R4_REAL_LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r14r4_run_20260804_f5b8348_v1.log"
SOURCE_R4_POST_LOG="${PROJECT_DIR}/logs/nohup/stage4_2r3c3t13s24d1r14r4_postprocess_20260804_f5b8348_v1.log"
for path in "${SOURCE_R4_REAL_LOG}" "${SOURCE_R4_POST_LOG}"; do
  [[ -f "${path}" ]] || { echo "ERROR: immutable R4 log missing: ${path}" >&2; exit 1; }
done

OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R14R5_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r5_new_output)}"
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: fresh D1R14R5 output exists: ${OUTPUT_DIR}" >&2; exit 1; }
stage4_2r3c3t13s24d1r14r5_export_runtime
printf '[T13S24D1R14R5] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[T13S24D1R14R5] source_r4=%s\nsource_r2=%s\noutput=%s\n' "${SOURCE_R4_RUN}" "${SOURCE_R2_RUN}" "${OUTPUT_DIR}"
printf '[T13S24D1R14R5] zero controller/plant/Ray/gotsc/TSC; 272 source raw are read in place.\n'
cd "${PROJECT_DIR}"
common_args=(
  --project "${PROJECT_DIR}"
  --config "${STAGE4_2R3C3T13S24D1R14R5_CONFIG}"
  --design-document "${STAGE4_2R3C3T13S24D1R14R5_DESIGN}"
  --source-r4-run "${SOURCE_R4_RUN}"
  --source-r2-run "${SOURCE_R2_RUN}"
  --source-r4-real-log "${SOURCE_R4_REAL_LOG}"
  --source-r4-postprocess-log "${SOURCE_R4_POST_LOG}"
)
"${STAGE4_2R3C3T13S24D1R14R5_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight.py \
  "${common_args[@]}" --output "${OUTPUT_DIR}"
"${STAGE4_2R3C3T13S24D1R14R5_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r5_independent_forensics.py \
  "${common_args[@]}" --primary-output "${OUTPUT_DIR}" \
  --output "${OUTPUT_DIR}/stage4_2r3c3t13s24d1r14r5_independent_v1.json"
printf '[T13S24D1R14R5] completed; no TSC task was created.\n'
