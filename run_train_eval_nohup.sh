#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONFIG="${1:-configs/train_b83_192worker_5m.json}"
LOG_DIR="logs/nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
CONFIG_BASENAME="$(basename "$CONFIG" .json)"
LOG_FILE="${LOG_DIR}/${CONFIG_BASENAME}_train_eval_${STAMP}.log"
PID_FILE="${PID_DIR}/${CONFIG_BASENAME}_train_eval_${STAMP}.pid"

echo "Starting B8.3 train + multi-stage eval with nohup..."
echo "Config: $CONFIG"
echo "Log:    $LOG_FILE"
echo "PID:    $PID_FILE"
echo

# run_train_eval_native.sh does train -> analyze -> eval in one foreground process.
nohup setsid bash run_train_eval_native.sh "$CONFIG" > "$LOG_FILE" 2>&1 < /dev/null &
PID=$!
echo "$PID" > "$PID_FILE"
ln -sfn "$(basename "$PID_FILE")" "${PID_DIR}/latest.pid"
ln -sfn "$(basename "$LOG_FILE")" "${LOG_DIR}/latest.log"

echo "Started."
echo "PID: $PID"
echo "Log: $LOG_FILE"
echo
echo "Monitor:"
echo "  tail -f ${LOG_DIR}/latest.log"
echo
echo "Stop:"
echo "  bash stop_train_nohup.sh"
