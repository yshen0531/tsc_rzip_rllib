#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${STAGE4_2R3C3T13S24D1R14R8R3_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r3_shell_common.sh"
stage4_2r3c3t13s24d1r14r8r3_validate
stage4_2r3c3t13s24d1r14r8r3_export

common_args=(
  --config "${STAGE4_2R3C3T13S24D1R14R8R3_CONFIG}"
  --r8r2-output "${STAGE4_2R3C3T13S24D1R14R8R3_R8R2_OUTPUT}"
  --r8-run "${STAGE4_2R3C3T13S24D1R14R8R3_R8_RUN}"
  --source-r2-run "${STAGE4_2R3C3T13S24D1R14R8R3_R2_RUN}"
  --source-r4-run "${STAGE4_2R3C3T13S24D1R14R8R3_R4_RUN}"
  --source-r6-run "${STAGE4_2R3C3T13S24D1R14R8R3_R6_RUN}"
)

case "${STAGE4_2R3C3T13S24D1R14R8R3_COMMAND}" in
  self-test)
    exec "${STAGE4_2R3C3T13S24D1R14R8R3_PYTHON}" -c \
      "from pathlib import Path; from tsc_rzip_rllib.diagnostics.stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer import self_test; print(self_test(Path(r'${STAGE4_2R3C3T13S24D1R14R8R3_CONFIG}')))"
    ;;
  primary)
    output="${STAGE4_2R3C3T13S24D1R14R8R3_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r8r3_new_output)}"
    exec "${STAGE4_2R3C3T13S24D1R14R8R3_PYTHON}" \
      "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer.py" \
      "${common_args[@]}" --output-dir "${output}"
    ;;
  independent)
    : "${STAGE4_2R3C3T13S24D1R14R8R3_OUTPUT_DIR:?set the accepted primary output directory}"
    exec "${STAGE4_2R3C3T13S24D1R14R8R3_PYTHON}" \
      "${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r3_independent_forensics.py" \
      "${common_args[@]}" --output-dir "${STAGE4_2R3C3T13S24D1R14R8R3_OUTPUT_DIR}"
    ;;
esac
