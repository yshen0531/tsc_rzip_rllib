#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup stage2_runs
export STAGE2_RUN_DIR="stage2_runs/stage2_svd3_real_tsc_cem_100ms_$(date +%Y%m%d_%H%M%S)"
LOG="logs/nohup/stage2_svd3_cem_$(date +%Y%m%d_%H%M%S).log"
printf '%s\n' "$STAGE2_RUN_DIR" > stage2_runs/latest_stage2_run.txt
nohup setsid env STAGE2_RUN_DIR="$STAGE2_RUN_DIR" SOURCE_STAGE1_1_RUN="${SOURCE_STAGE1_1_RUN:-}" \
  STAGE2_TSC_WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}" \
  STAGE2_TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-/tmp/tsc_workspace/episode_runs}" \
  ./run_stage2_svd3_cem_native.sh >"$LOG" 2>&1 &
echo $! > stage2_runs/stage2_driver.pid
ln -sfn "$(basename "$LOG")" logs/nohup/latest_stage2_svd3_cem.log
echo "[Stage2] pid=$(cat stage2_runs/stage2_driver.pid)"
echo "[Stage2] run_dir=$STAGE2_RUN_DIR"
echo "[Stage2] log=$LOG"
