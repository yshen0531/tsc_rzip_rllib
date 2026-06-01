#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(dirname "$PROJECT_DIR")}"

CONFIG=${1:-configs/mpo_b85_recurrent_192worker_5m.json}
OVERRIDE=${2:-}
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p logs/nohup logs/pids
LOG="logs/nohup/train_mpo_${STAMP}.log"
ln -sfn "$(basename "$LOG")" logs/nohup/latest_mpo.log

if [[ -n "$OVERRIDE" ]]; then
  nohup bash run_train_mpo_native.sh "$CONFIG" "$OVERRIDE" > "$LOG" 2>&1 &
else
  nohup bash run_train_mpo_native.sh "$CONFIG" > "$LOG" 2>&1 &
fi
PID=$!
echo "$PID" > logs/pids/latest_train_mpo.pid

echo "Started B85 MPO training. pid=$PID"
echo "Log: $LOG"
echo "Follow: tail -f logs/nohup/latest_mpo.log"
