#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3c_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3c_shell_common.sh"
stage4_2r3c_validate_common
SOURCE_R3B="$(stage4_2r3c_find_source_r3b)" || exit 1
RUN_DIR="${STAGE4_2R3C_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" ]]; then
  LATEST="${STAGE4_2R3C_OUTPUT_ROOT}/latest_stage4_2r3c_run.txt"
  [[ -f "${LATEST}" ]] || {
    echo "ERROR: Stage4.2R3c latest-run pointer missing" >&2
    exit 1
  }
  RUN_DIR="$(tr -d '\r\n' < "${LATEST}")"
fi
[[ -d "${RUN_DIR}" ]] || {
  echo "ERROR: Stage4.2R3c run directory missing: ${RUN_DIR}" >&2
  exit 1
}
AUDIT_ROOT="${STAGE4_2R3C_AUDIT_ROOT:-${PROJECT_DIR}/stage4_2r3c_audits}"
OUTPUT_DIR="${STAGE4_2R3C_AUDIT_DIR:-${AUDIT_ROOT}/$(basename "${RUN_DIR}")}"
mkdir -p "${OUTPUT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3C_PYTHON}" \
  "${PROJECT_DIR}/scripts/stage4_2r3c_server_postprocess.py" \
  --config "${STAGE4_2R3C_CONFIG}" \
  --source-stage4-2r3b-run "${SOURCE_R3B}" \
  --run-dir "${RUN_DIR}" \
  --output-dir "${OUTPUT_DIR}"
