#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage4_2r3_shell_common.sh
source "${PROJECT_DIR}/scripts/stage4_2r3_shell_common.sh"
stage4_2r3_validate_common
SOURCE_R2="$(stage4_2r3_find_source_r2)" || {
  echo "ERROR: no complete certified Stage4.2R2 source run found" >&2
  exit 1
}
RUN_DIR="${STAGE4_2R3_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" ]]; then
  LATEST="${STAGE4_2R3_OUTPUT_ROOT}/latest_stage4_2r3_run.txt"
  [[ -f "${LATEST}" ]] || {
    echo "ERROR: Stage4.2R3 latest-run pointer missing" >&2
    exit 1
  }
  RUN_DIR="$(tr -d '\r\n' < "${LATEST}")"
fi
[[ -d "${RUN_DIR}" ]] || {
  echo "ERROR: Stage4.2R3 run directory missing: ${RUN_DIR}" >&2
  exit 1
}
AUDIT_ROOT="${STAGE4_2R3_AUDIT_ROOT:-${PROJECT_DIR}/stage4_2r3_audits}"
OUTPUT_DIR="${STAGE4_2R3_AUDIT_DIR:-${AUDIT_ROOT}/$(basename "${RUN_DIR}")}"
mkdir -p "${OUTPUT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${STAGE4_2R3_PYTHON}" \
  "${PROJECT_DIR}/scripts/stage4_2r3_server_postprocess.py" \
  --config "${STAGE4_2R3_CONFIG}" \
  --source-stage4-2r2-run "${SOURCE_R2}" \
  --run-dir "${RUN_DIR}" \
  --output-dir "${OUTPUT_DIR}"
