#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s13_shell_common.sh"
stage4_2r3c3t13s13_validate_common
RUN_DIR="${STAGE4_2R3C3T13S13_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" ]]; then
  LATEST="${STAGE4_2R3C3T13S13_OUTPUT_ROOT}/latest_stage4_2r3c3t13s13_run.txt"
  [[ -f "${LATEST}" ]] || { echo "ERROR: T13S13 latest-run pointer missing" >&2; exit 1; }
  RUN_DIR="$(tr -d '\r\n' < "${LATEST}")"
fi
[[ -d "${RUN_DIR}" ]] || { echo "ERROR: T13S13 run directory missing" >&2; exit 1; }
AUDIT_ROOT="${STAGE4_2R3C3T13S13_AUDIT_ROOT:-${PROJECT_DIR}/stage4_2r3c3t13s13_audits}"
AUDIT_DIR="${STAGE4_2R3C3T13S13_AUDIT_DIR:-${AUDIT_ROOT}/$(basename "${RUN_DIR}")}"
mkdir -p "${AUDIT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C3T13S13_PYTHON}" "${PROJECT_DIR}/scripts/stage4_2r3c3t13s13_server_postprocess.py" \
  --config "${STAGE4_2R3C3T13S13_CONFIG}" \
  --source-stage4-2r3b-run "$(stage4_2r3c3t13s13_find_source_r3b)" \
  --source-stage4-2r3c3-run "$(stage4_2r3c3t13s13_find_source_r3c3)" \
  --source-stage4-2r3c3-bank-dir "$(stage4_2r3c3t13s13_find_source_bank)" \
  --source-stage4-2r3c3t1-run "$(stage4_2r3c3t13s13_find_source_t1)" \
  --source-stage4-2r3c3t1-audit-dir "$(stage4_2r3c3t13s13_find_source_t1_audit)" \
  --source-stage4-2r3c3t3-controller-bank "$(stage4_2r3c3t13s13_find_t3_controller_bank)" \
  --q1-run "$(stage4_2r3c3t13s13_q1_run)" --q2-run "$(stage4_2r3c3t13s13_q2_run)" \
  --q1-audit "$(stage4_2r3c3t13s13_q1_audit)" --q2-audit "$(stage4_2r3c3t13s13_q2_audit)" \
  --r3b-server-audit "$(stage4_2r3c3t13s13_r3b_audit)" \
  --r3b-snapshot-checks "$(stage4_2r3c3t13s13_r3b_snapshot_checks)" \
  --run-dir "${RUN_DIR}" --audit-dir "${AUDIT_DIR}"
