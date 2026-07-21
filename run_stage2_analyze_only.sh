#!/usr/bin/env bash
set -euo pipefail
export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
if [[ -z "${STAGE2_RUN_DIR:-}" ]]; then
  STAGE2_RUN_DIR="$(cat stage2_runs/latest_stage2_run.txt)"
fi
CONFIG="${STAGE2_CONFIG:-configs/stage2_svd3_real_tsc_cem_100ms.json}"
exec python -u scripts/stage2_trajectory_optimization.py analyze \
  --config "$CONFIG" --run-dir "$STAGE2_RUN_DIR" --backend serial
