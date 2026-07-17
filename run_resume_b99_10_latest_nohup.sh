#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_10_resume_b99_9_train_first_train.log"
PIDFILE="logs/nohup/latest_b99_10_resume_b99_9_train_first_train.pid"
nohup setsid ./run_resume_b99_10_latest_native.sh > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Resumed B99.10 process-group leader PID=$(cat "$PIDFILE")"
echo "Log: $LOG"
echo "Immediate stop: ./run_stop_b99_10_now.sh"
