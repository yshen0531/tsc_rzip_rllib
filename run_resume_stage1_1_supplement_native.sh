#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${STAGE1_1_RUN_DIR:-}" ]]; then
  STAGE1_1_RUN_DIR="$(cat stage1_1_runs/latest_stage1_1_run.txt)"
fi
export STAGE1_1_RUN_DIR
exec ./run_stage1_1_supplement_native.sh
