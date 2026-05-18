#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONFIG="${1:-configs/train_b81_96worker_100k.json}"

LOG_DIR="logs/nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
CONFIG_BASENAME="$(basename "$CONFIG" .json)"
LOG_FILE="${LOG_DIR}/${CONFIG_BASENAME}_${STAMP}.log"
PID_FILE="${PID_DIR}/${CONFIG_BASENAME}_${STAMP}.pid"

echo "Starting nohup training..."
echo "Config: $CONFIG"
echo "Log:    $LOG_FILE"
echo "PID:    $PID_FILE"

nohup bash run_train_native.sh "$CONFIG" > "$LOG_FILE" 2>&1 < /dev/null &
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
