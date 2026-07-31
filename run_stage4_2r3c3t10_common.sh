#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t10_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t10_shell_common.sh"
stage4_2r3c3t10_validate_common
SOURCE_R3B="$(stage4_2r3c3t9_find_source_r3b)" || exit 1
SOURCE_R3C3="$(stage4_2r3c3t9_find_source_r3c3)" || exit 1
SOURCE_BANK="$(stage4_2r3c3t9_find_source_bank)" || exit 1
SOURCE_T1="$(stage4_2r3c3t9_find_source_t1)" || exit 1
SOURCE_T1_AUDIT="$(stage4_2r3c3t9_find_source_t1_audit)" || exit 1
SOURCE_T7_BANK="$(stage4_2r3c3t9_find_t7_controller_bank)" || exit 1
SOURCE_T9_RUN="$(stage4_2r3c3t10_find_t9_run)" || exit 1
SOURCE_T9_AUDIT="$(stage4_2r3c3t10_find_t9_audit)" || exit 1
FORMAL_EVALUATOR="${PROJECT_DIR}/docs/codex/audit_tools/stage4_2r3c3t1_six_basis_feasibility_diagnostic.py"
if [[ -n "${STAGE4_2R3C3T10_OUTPUT_DIR:-}" ]]; then
  OUTPUT_DIR="${STAGE4_2R3C3T10_OUTPUT_DIR}"
else
  OUTPUT_DIR="$(stage4_2r3c3t10_new_output_dir)"
fi
[[ ! -e "${OUTPUT_DIR}" ]] || {
  echo "ERROR: T10 output must be a new path: ${OUTPUT_DIR}" >&2
  exit 1
}
stage4_2r3c3t10_export_runtime
printf '[Stage4.2R3c3T10] user=%s host=%s pwd=%s\n' "$(id -un)" "$(hostname)" "$(pwd)"
printf '[Stage4.2R3c3T10] source_t9_run=%s\nsource_t9_audit=%s\noutput=%s\n' \
  "${SOURCE_T9_RUN}" "${SOURCE_T9_AUDIT}" "${OUTPUT_DIR}"
printf '[Stage4.2R3c3T10] read-only offline audit: no new TSC and no real MPC.\n'
printf '[Stage4.2R3c3T10] Formal 250/270 and 350/370 ms timing is unchanged.\n'
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T10_PYTHON}" \
  docs/codex/audit_tools/stage4_2r3c3t10_interaction_aware_feasibility.py \
  --config "${STAGE4_2R3C3T10_CONFIG}" \
  --t9-config "${STAGE4_2R3C3T10_T9_CONFIG}" \
  --source-stage4-2r3b-run "${SOURCE_R3B}" \
  --source-stage4-2r3c3-run "${SOURCE_R3C3}" \
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}" \
  --source-stage4-2r3c3t1-run "${SOURCE_T1}" \
  --source-stage4-2r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" \
  --source-stage4-2r3c3t7-controller-bank "${SOURCE_T7_BANK}" \
  --source-stage4-2r3c3t9-run "${SOURCE_T9_RUN}" \
  --source-stage4-2r3c3t9-audit-dir "${SOURCE_T9_AUDIT}" \
  --frozen-formal-evaluator "${FORMAL_EVALUATOR}" \
  --output "${OUTPUT_DIR}"
