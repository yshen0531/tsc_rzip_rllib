#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_7_resume_b99_6_best_error_train.log"
nohup ./run_train_b99_7_resume_b99_6_best_error_native.sh > "$LOG" 2>&1 &
echo $! > logs/nohup/latest_b99_7_resume_b99_6_best_error_train.pid
echo "Started B99.7 resume training PID=$(cat logs/nohup/latest_b99_7_resume_b99_6_best_error_train.pid)"
echo "Log: $LOG"
