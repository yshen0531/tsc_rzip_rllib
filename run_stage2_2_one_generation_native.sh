#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_2_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_2_shell_common.sh"
stage22_project_init
stage22_find_python
if [[ -z "${STAGE2_2_RUN_DIR:-}" && -f "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt" ]]; then
  candidate="$(head -n 1 "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt" | tr -d '\r')"
  if [[ -n "${candidate}" ]]; then
    candidate="$(stage22_abspath "${candidate}")"
    if [[ -f "${candidate}/stage2_2_state.json" ]]; then
      export STAGE2_2_RUN_DIR="${candidate}"
      export STAGE2_2_RESUME=1
    fi
  fi
fi
export STAGE2_2_COMMAND=generation
export STAGE2_2_BACKEND="${STAGE2_2_BACKEND:-ray}"
exec bash "${PROJECT_DIR}/run_stage2_2_svd3_corner_native.sh"
