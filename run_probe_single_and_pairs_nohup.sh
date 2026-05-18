#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

NUM_WORKERS="${1:-16}"

LOG_DIR="logs/probe_nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/probe_single_and_pairs_${STAMP}.log"
PID_FILE="${PID_DIR}/probe_single_and_pairs_${STAMP}.pid"

echo "Starting single-coil + U/L pair controllability probe..."
echo "NUM_WORKERS: $NUM_WORKERS"
echo "Log: $LOG_FILE"
echo "PID: $PID_FILE"
echo

nohup setsid bash run_probe_controllability.sh \
  --config configs/rllib_sac.json \
  --horizon-steps 250 \
  --pulse-steps 20,50,100 \
  --response-step 100 \
  --response-steps 20,50,100,150,250 \
  --amplitudes 1.0 \
  --include-pairs \
  --num-workers "$NUM_WORKERS" \
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
echo "Check workers:"
echo "  ps -eLo pid,ppid,tid,psr,pcpu,stat,comm,args | grep -E \"probe_controllability.py|gotsc|python\" | grep -v grep | head -100"
echo
echo "Stop:"
echo "  bash stop_probe_controllability.sh"