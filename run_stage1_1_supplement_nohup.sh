#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup stage1_1_runs
export STAGE1_1_RUN_DIR="${STAGE1_1_RUN_DIR:-stage1_1_runs/stage1_1_svd234_strict_validation_100ms_$(date +%Y%m%d_%H%M%S)}"
LOG="logs/nohup/stage1_1_supplement_$(date +%Y%m%d_%H%M%S).log"
printf '%s\n' "$STAGE1_1_RUN_DIR" > stage1_1_runs/latest_stage1_1_run.txt
nohup env STAGE1_1_RUN_DIR="$STAGE1_1_RUN_DIR" SOURCE_STAGE1_RUN="${SOURCE_STAGE1_RUN:-}" \
  ./run_stage1_1_supplement_native.sh >"$LOG" 2>&1 &
echo $! > stage1_1_runs/stage1_1_driver.pid
ln -sfn "$(basename "$LOG")" logs/nohup/latest_stage1_1_supplement.log
echo "[Stage1.1] pid=$(cat stage1_1_runs/stage1_1_driver.pid)"
echo "[Stage1.1] run_dir=$STAGE1_1_RUN_DIR"
echo "[Stage1.1] log=$LOG"
