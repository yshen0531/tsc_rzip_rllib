#!/usr/bin/env bash
set -euo pipefail
mkdir -p logs/nohup
LOG="logs/nohup/latest_b99_10_resume_b99_9_train_first_train.log"
PIDFILE="logs/nohup/latest_b99_10_resume_b99_9_train_first_train.pid"
# setsid gives the job its own process group so run_stop_b99_10_now.sh can
# terminate the driver and children immediately without graceful handling.
nohup setsid ./run_train_b99_10_resume_b99_9_train_first_native.sh > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Started B99.10 process-group leader PID=$(cat "$PIDFILE")"
echo "Log: $LOG"
echo "Immediate stop: ./run_stop_b99_10_now.sh"
