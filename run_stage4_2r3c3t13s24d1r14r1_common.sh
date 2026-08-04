#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r1_shell_common.sh"
stage4_2r3c3t13s24d1r14r1_validate_common
SOURCE_RUN="${PROJECT_DIR}/stage4_2r3c3t13s24d1r14_runs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_d32761c_v1"
OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R14R1_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r1_new_output_dir)}"
[[ -d "${SOURCE_RUN}" ]] || { echo "ERROR: immutable D1R14 v2 source run missing" >&2; exit 1; }
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: D1R14R1 output path exists: ${OUTPUT_DIR}" >&2; exit 1; }
stage4_2r3c3t13s24d1r14r1_export_runtime
printf '[Stage4.2R3c3T13S24D1R14R1] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T13S24D1R14R1] source=%s\noutput=%s\n' "${SOURCE_RUN}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T13S24D1R14R1] zero controller/plant/Ray/gotsc/TSC; read immutable raw in place.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R14R1_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight.py \
  --project "${PROJECT_DIR}" \
  --config "${STAGE4_2R3C3T13S24D1R14R1_CONFIG}" \
  --design-document "${STAGE4_2R3C3T13S24D1R14R1_DESIGN}" \
  --source-run "${SOURCE_RUN}" \
  --output "${OUTPUT_DIR}"
