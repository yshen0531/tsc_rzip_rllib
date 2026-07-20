#!/usr/bin/env bash
set -euo pipefail
export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "$PROJECT_DIR/.." && pwd)}"
export STAGE2_WORKERS="${STAGE2_WORKERS:-6}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_confirm_$(id -u)}"
export TMPDIR="$RAY_TMPDIR/tmp"
mkdir -p "$TMPDIR"
if [[ -z "${STAGE2_RUN_DIR:-}" ]]; then
  STAGE2_RUN_DIR="$(cat stage2_runs/latest_stage2_run.txt)"
fi
CONFIG="${STAGE2_CONFIG:-configs/stage2_svd3_real_tsc_cem_100ms.json}"
python -u scripts/stage2_trajectory_optimization.py confirm \
  --config "$CONFIG" --run-dir "$STAGE2_RUN_DIR" --backend ray
python -u scripts/stage2_trajectory_optimization.py analyze \
  --config "$CONFIG" --run-dir "$STAGE2_RUN_DIR" --backend serial
