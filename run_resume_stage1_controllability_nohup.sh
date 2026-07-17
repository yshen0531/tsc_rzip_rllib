#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${STAGE1_RUN_DIR:-}" ]]; then
  STAGE1_RUN_DIR="$(cat stage1_runs/latest_stage1_run.txt)"
fi
export STAGE1_RUN_DIR
exec ./run_stage1_controllability_nohup.sh
