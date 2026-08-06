#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R8R2_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r2_shell_common.sh"
stage4_2r3c3t13s24d1r14r8r2_validate
stage4_2r3c3t13s24d1r14r8r2_export

common_args=(
  --config "${STAGE4_2R3C3T13S24D1R14R8R2_CONFIG}"
  --r8r1-output "${STAGE4_2R3C3T13S24D1R14R8R2_R8R1_OUTPUT}"
  --r8-run "${STAGE4_2R3C3T13S24D1R14R8R2_R8_RUN}"
  --source-r2-run "${STAGE4_2R3C3T13S24D1R14R8R2_R2_RUN}"
  --source-r4-run "${STAGE4_2R3C3T13S24D1R14R8R2_R4_RUN}"
  --source-r6-run "${STAGE4_2R3C3T13S24D1R14R8R2_R6_RUN}"
)

case "${STAGE4_2R3C3T13S24D1R14R8R2_COMMAND}" in
  self-test)
    exec "${STAGE4_2R3C3T13S24D1R14R8R2_PYTHON}" -c \
      "from pathlib import Path; from tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation import self_test; print(self_test(Path(r'${STAGE4_2R3C3T13S24D1R14R8R2_CONFIG}')))"
    ;;
  primary)
    output="${STAGE4_2R3C3T13S24D1R14R8R2_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r8r2_new_output)}"
    exec "${STAGE4_2R3C3T13S24D1R14R8R2_PYTHON}" \
      "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation.py" \
      "${common_args[@]}" --output-dir "${output}"
    ;;
  independent)
    : "${STAGE4_2R3C3T13S24D1R14R8R2_OUTPUT_DIR:?set the accepted primary output directory}"
    exec "${STAGE4_2R3C3T13S24D1R14R8R2_PYTHON}" \
      "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r2_independent_forensics.py" \
      "${common_args[@]}" --output-dir "${STAGE4_2R3C3T13S24D1R14R8R2_OUTPUT_DIR}"
    ;;
esac
