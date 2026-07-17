#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup stage1_runs
export STAGE1_RUN_DIR="${STAGE1_RUN_DIR:-stage1_runs/stage1_controllability_100ms_$(date +%Y%m%d_%H%M%S)}"
LOG="logs/nohup/stage1_controllability_$(date +%Y%m%d_%H%M%S).log"
printf '%s\n' "$STAGE1_RUN_DIR" > stage1_runs/latest_stage1_run.txt
nohup env STAGE1_RUN_DIR="$STAGE1_RUN_DIR" ./run_stage1_controllability_native.sh >"$LOG" 2>&1 &
echo $! > stage1_runs/stage1_driver.pid
ln -sfn "$(basename "$LOG")" logs/nohup/latest_stage1_controllability.log
echo "[Stage1] pid=$(cat stage1_runs/stage1_driver.pid)"
echo "[Stage1] run_dir=$STAGE1_RUN_DIR"
echo "[Stage1] log=$LOG"
