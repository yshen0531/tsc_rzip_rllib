#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

LOG_DIR="logs/eval_sweep_nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/eval_checkpoint_sweep_${STAMP}.log"
PID_FILE="${PID_DIR}/eval_checkpoint_sweep_${STAMP}.pid"

echo "Starting checkpoint sweep with nohup..."
echo "Log: $LOG_FILE"
echo "PID: $PID_FILE"
echo
echo "Command:"
echo "  ./run_eval_checkpoint_sweep.sh $*"
echo

nohup setsid bash run_eval_checkpoint_sweep.sh "$@" \
  > "$LOG_FILE" 2>&1 < /dev/null &

PID=$!
echo "$PID" > "$PID_FILE"

ln -sfn "$PID_FILE" "${PID_DIR}/latest_eval_sweep.pid"
ln -sfn "$LOG_FILE" "${LOG_DIR}/latest.log"

echo "Started."
echo "PID: $PID"
echo "Log: $LOG_FILE"
echo
echo "Monitor:"
echo "  tail -f ${LOG_DIR}/latest.log"
echo
echo "Stop:"
echo "  bash stop_eval_checkpoint_sweep.sh"
