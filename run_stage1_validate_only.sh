#!/usr/bin/env bash
set -euo pipefail
RUN_DIR="${STAGE1_RUN_DIR:-$(cat stage1_runs/latest_stage1_run.txt)}"
python -u scripts/stage1_controllability.py validate \
  --config "${STAGE1_CONFIG:-configs/stage1_controllability_100ms.json}" \
  --run-dir "$RUN_DIR" \
  --backend ray
