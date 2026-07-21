#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/stage2_1_shell_common.sh
source "${SCRIPT_DIR}/scripts/stage2_1_shell_common.sh"
stage21_project_init
stage21_find_python

if [[ -z "${STAGE2_1_RUN_DIR:-}" && -f "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt" ]]; then
  candidate="$(head -n 1 "${PROJECT_DIR}/stage2_1_runs/latest_stage2_1_run.txt" | tr -d '\r')"
  if [[ -n "${candidate}" ]]; then
    candidate="$(stage21_abspath "${candidate}")"
    if [[ -f "${candidate}/stage2_1_state.json" ]]; then
      export STAGE2_1_RUN_DIR="${candidate}"
      export STAGE2_1_RESUME=1
    fi
  fi
fi
export STAGE2_1_COMMAND=generation
export STAGE2_1_BACKEND="${STAGE2_1_BACKEND:-ray}"
exec bash "${PROJECT_DIR}/run_stage2_1_svd3_dual_archive_native.sh"
