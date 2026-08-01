#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c3t13s1_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s1_shell_common.sh"
stage4_2r3c3t13s1_validate_common
SOURCE_R3B="$(stage4_2r3c3t13s1_find_source_r3b)" || exit 1
SOURCE_R3C3="$(stage4_2r3c3t13s1_find_source_r3c3)" || exit 1
SOURCE_BANK="$(stage4_2r3c3t13s1_find_source_bank)" || exit 1
SOURCE_T1="$(stage4_2r3c3t13s1_find_source_t1)" || exit 1
SOURCE_T1_AUDIT="$(stage4_2r3c3t13s1_find_source_t1_audit)" || exit 1
SOURCE_T3_BANK="$(stage4_2r3c3t13s1_find_t3_controller_bank)" || exit 1
RUN_DIR="${STAGE4_2R3C3T13S1_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" ]]; then
  LATEST="${STAGE4_2R3C3T13S1_OUTPUT_ROOT}/latest_stage4_2r3c3t13s1_run.txt"
  [[ -f "${LATEST}" ]] || {
    echo "ERROR: Stage4.2R3c3T13S1 latest-run pointer missing" >&2
    exit 1
  }
  RUN_DIR="$(tr -d '\r\n' < "${LATEST}")"
fi
[[ -d "${RUN_DIR}" ]] || {
  echo "ERROR: Stage4.2R3c3T13S1 run directory missing: ${RUN_DIR}" >&2
  exit 1
}
AUDIT_ROOT="${STAGE4_2R3C3T13S1_AUDIT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s1_audits}"
AUDIT_DIR="${STAGE4_2R3C3T13S1_AUDIT_DIR:-${AUDIT_ROOT}/$(basename "${RUN_DIR}")}"
mkdir -p "${AUDIT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C3T13S1_PYTHON}" \
  "${PROJECT_DIR}/scripts/stage4_2r3c3t13s1_server_postprocess.py" \
  --config "${STAGE4_2R3C3T13S1_CONFIG}" \
  --source-stage4-2r3b-run "${SOURCE_R3B}" \
  --source-stage4-2r3c3-run "${SOURCE_R3C3}" \
  --source-stage4-2r3c3-bank-dir "${SOURCE_BANK}" \
  --source-stage4-2r3c3t1-run "${SOURCE_T1}" \
  --source-stage4-2r3c3t1-audit-dir "${SOURCE_T1_AUDIT}" \
  --source-stage4-2r3c3t3-controller-bank "${SOURCE_T3_BANK}" \
  --run-dir "${RUN_DIR}" \
  --audit-dir "${AUDIT_DIR}"
