#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r8r1_shell_common.sh"
stage4_2r3c3t13s24d1r14r8r1_validate
stage4_2r3c3t13s24d1r14r8r1_export
cd "${PROJECT_DIR}"
if [[ "${STAGE4_2R3C3T13S24D1R14R8R1_COMMAND}" == self-test ]]; then
  exec "${STAGE4_2R3C3T13S24D1R14R8R1_PYTHON}" -c \
    "from pathlib import Path; from tsc_rzip_rllib.diagnostics import stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as m; print(m.self_test(Path('${STAGE4_2R3C3T13S24D1R14R8R1_CONFIG}')))"
fi
[[ -n "${STAGE4_2R3C3T13S24D1R14R8R1_OUTPUT_DIR:-}" ]] || { echo 'ERROR: output dir required' >&2; exit 1; }
args=(--config "${STAGE4_2R3C3T13S24D1R14R8R1_CONFIG}" --r8-run "${STAGE4_2R3C3T13S24D1R14R8R1_R8_RUN}" --source-r2-run "${STAGE4_2R3C3T13S24D1R14R8R1_R2_RUN}" --source-r4-run "${STAGE4_2R3C3T13S24D1R14R8R1_R4_RUN}" --source-r6-run "${STAGE4_2R3C3T13S24D1R14R8R1_R6_RUN}" --output-dir "${STAGE4_2R3C3T13S24D1R14R8R1_OUTPUT_DIR}")
if [[ "${STAGE4_2R3C3T13S24D1R14R8R1_COMMAND}" == primary ]]; then
  exec "${STAGE4_2R3C3T13S24D1R14R8R1_PYTHON}" scripts/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.py "${args[@]}"
fi
exec "${STAGE4_2R3C3T13S24D1R14R8R1_PYTHON}" docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r1_independent_forensics.py "${args[@]}"
