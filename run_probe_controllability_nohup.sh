#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

LOG_DIR="logs/probe_nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/probe_controllability_${STAMP}.log"
PID_FILE="${PID_DIR}/probe_controllability_${STAMP}.pid"

echo "Starting controllability probe with nohup..."
echo "Log: $LOG_FILE"
echo "PID: $PID_FILE"
echo
echo "Command:"
echo "  ./run_probe_controllability.sh $*"
echo

# run_probe_controllability.sh sets all thread limits before importing NumPy.
nohup setsid bash run_probe_controllability.sh "$@" \
  > "$LOG_FILE" 2>&1 < /dev/null &

PID=$!
echo "$PID" > "$PID_FILE"

ln -sfn "$PID_FILE" "${PID_DIR}/latest_probe.pid"
ln -sfn "$LOG_FILE" "${LOG_DIR}/latest.log"

echo "Started."
echo "PID: $PID"
echo "Log: $LOG_FILE"
echo
echo "Monitor:"
echo "  tail -f ${LOG_DIR}/latest.log"
echo
echo "Stop:"
echo "  bash stop_probe_controllability.sh"