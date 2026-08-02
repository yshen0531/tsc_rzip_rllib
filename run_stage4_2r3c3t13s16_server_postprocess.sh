#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s16_shell_common.sh"
RUN_DIR="${STAGE4_2R3C3T13S16_RUN_DIR:-}"
if [[ -z "${RUN_DIR}" ]]; then
  LATEST="${STAGE4_2R3C3T13S16_OUTPUT_ROOT}/latest_stage4_2r3c3t13s16_run.txt"
  [[ -f "${LATEST}" ]] || { echo "ERROR: T13S16 latest-run pointer missing" >&2; exit 1; }
  RUN_DIR="$(tr -d '\r\n' < "${LATEST}")"
fi
export STAGE4_2R3C3T13S16_RUN_DIR="${RUN_DIR}"
export STAGE4_2R3C3T13S16_COMMAND=postprocess
export STAGE4_2R3C3T13S16_BACKEND=serial
export STAGE4_2R3C3T13S16_RESUME=1
exec bash "${PROJECT_DIR}/run_stage4_2r3c3t13s16_common.sh"
