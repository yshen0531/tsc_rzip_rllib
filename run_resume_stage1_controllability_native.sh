#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${STAGE1_RUN_DIR:-}" ]]; then
  if [[ -f stage1_runs/latest_stage1_run.txt ]]; then
    STAGE1_RUN_DIR="$(cat stage1_runs/latest_stage1_run.txt)"
  else
    echo "Set STAGE1_RUN_DIR=/path/to/existing/stage1 run." >&2
    exit 2
  fi
fi
export STAGE1_RUN_DIR
exec ./run_stage1_controllability_native.sh
