#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_6_resume_b99_5_iter25_train.log"
nohup ./run_train_b99_6_resume_b99_5_iter25_native.sh > "$LOG" 2>&1 &
echo $! > logs/nohup/latest_b99_6_resume_b99_5_iter25_train.pid
echo "Started B99.6 resume training PID=$(cat logs/nohup/latest_b99_6_resume_b99_5_iter25_train.pid)"
echo "Log: $LOG"
