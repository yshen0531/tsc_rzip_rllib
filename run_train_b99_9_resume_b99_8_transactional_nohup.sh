#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_9_resume_b99_8_transactional_train.log"
nohup ./run_train_b99_9_resume_b99_8_transactional_native.sh > "$LOG" 2>&1 &
echo $! > logs/nohup/latest_b99_9_resume_b99_8_transactional_train.pid
echo "Started B99.9 PID=$(cat logs/nohup/latest_b99_9_resume_b99_8_transactional_train.pid)"
echo "Log: $LOG"
