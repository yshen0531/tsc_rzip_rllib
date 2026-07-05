#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_4_train.log"
nohup ./run_train_b99_4_native.sh > "$LOG" 2>&1 &
echo $! > logs/nohup/latest_b99_4_train.pid
echo "Started B99.4 training PID=$(cat logs/nohup/latest_b99_4_train.pid)"
echo "Log: $LOG"
