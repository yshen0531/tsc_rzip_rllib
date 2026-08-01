#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t12_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t12_shell_common.sh"
stage4_2r3c3t12_validate_common
SOURCE_T11_RUN="$(stage4_2r3c3t12_find_t11_run)" || exit 1
SOURCE_T11_AUDIT="$(stage4_2r3c3t12_find_t11_audit)" || exit 1
if [[ -n "${STAGE4_2R3C3T12_OUTPUT_DIR:-}" ]]; then
  OUTPUT_DIR="${STAGE4_2R3C3T12_OUTPUT_DIR}"
else
  OUTPUT_DIR="$(stage4_2r3c3t12_new_output_dir)"
fi
[[ ! -e "${OUTPUT_DIR}" ]] || {
  echo "ERROR: T12 output must be a new path: ${OUTPUT_DIR}" >&2
  exit 1
}
stage4_2r3c3t12_export_runtime
printf '[Stage4.2R3c3T12] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T12] source_t11_run=%s\nsource_t11_audit=%s\noutput=%s\n' \
  "${SOURCE_T11_RUN}" "${SOURCE_T11_AUDIT}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T12] read-only source audit: no plant, controller, optimizer, or snapshot execution.\n'
printf '[Stage4.2R3c3T12] Formal 250/270 and 350/370 ms timing is unchanged.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T12_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t12_formal_gap_route_discriminator.py \
  --config "${STAGE4_2R3C3T12_CONFIG}" \
  --source-t11-run "${SOURCE_T11_RUN}" \
  --source-t11-audit-dir "${SOURCE_T11_AUDIT}" \
  --output "${OUTPUT_DIR}"
