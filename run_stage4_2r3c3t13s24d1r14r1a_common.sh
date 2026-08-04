#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s24d1r14r1a_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r14r1a_shell_common.sh"
stage4_2r3c3t13s24d1r14r1a_validate_common
SOURCE_R1="${PROJECT_DIR}/stage4_2r3c3t13s24d1r14r1_audits/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_20260804_36f0d41_v1"
SOURCE_D1R14="${PROJECT_DIR}/stage4_2r3c3t13s24d1r14_runs/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel_20260804_d32761c_v1"
OUTPUT_DIR="${STAGE4_2R3C3T13S24D1R14R1A_OUTPUT_DIR:-$(stage4_2r3c3t13s24d1r14r1a_new_output_dir)}"
[[ -d "${SOURCE_R1}" ]] || { echo "ERROR: immutable R1 source missing" >&2; exit 1; }
[[ -d "${SOURCE_D1R14}" ]] || { echo "ERROR: immutable D1R14 source missing" >&2; exit 1; }
[[ ! -e "${OUTPUT_DIR}" ]] || { echo "ERROR: D1R14R1A output path exists: ${OUTPUT_DIR}" >&2; exit 1; }
stage4_2r3c3t13s24d1r14r1a_export_runtime
printf '[Stage4.2R3c3T13S24D1R14R1A] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T13S24D1R14R1A] source_r1=%s\nsource_d1r14=%s\noutput=%s\n' "${SOURCE_R1}" "${SOURCE_D1R14}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T13S24D1R14R1A] zero controller/plant/Ray/gotsc/TSC; fixed candidate replay only.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R14R1A_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight.py \
  --project "${PROJECT_DIR}" \
  --config "${STAGE4_2R3C3T13S24D1R14R1A_CONFIG}" \
  --design-document "${STAGE4_2R3C3T13S24D1R14R1A_DESIGN}" \
  --source-r1-output "${SOURCE_R1}" \
  --source-d1r14-run "${SOURCE_D1R14}" \
  --output "${OUTPUT_DIR}"
