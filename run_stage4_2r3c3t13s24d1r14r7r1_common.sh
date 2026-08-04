#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)";source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r7r1_shell_common.sh";stage4_2r3c3t13s24d1r14r7r1_validate;stage4_2r3c3t13s24d1r14r7r1_export
R2="$(stage4_2r3c3t13s24d1r14r7r1_source r2)";R4="$(stage4_2r3c3t13s24d1r14r7r1_source r4)";R6="$(stage4_2r3c3t13s24d1r14r7r1_source r6)"
OUTPUT="${STAGE4_2R3C3T13S24D1R14R7R1_OUTPUT_DIR:-${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r7r1_audits/stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model_$(date -u +%Y%m%d_%H%M%S)}";[[ ! -e "${OUTPUT}" ]]
printf '[T13S24D1R14R7R1] zero controller/plant/Ray/gotsc/TSC; 320 source raw read in place.\n'
cd "${PROJECT_DIR}";args=(--config "${STAGE4_2R3C3T13S24D1R14R7R1_CONFIG}" --design-document "${STAGE4_2R3C3T13S24D1R14R7R1_DESIGN}" --source-r2-run "${R2}" --source-r4-run "${R4}" --source-r6-run "${R6}")
"${STAGE4_2R3C3T13S24D1R14R7R1_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model.py "${args[@]}" --output "${OUTPUT}"
"${STAGE4_2R3C3T13S24D1R14R7R1_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7r1_independent_forensics.py "${args[@]}" --primary-output "${OUTPUT}" --output "${OUTPUT}/stage4_2r3c3t13s24d1r14r7r1_independent_v1.json"
