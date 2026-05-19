#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PID_FILE="logs/pids/latest.pid"

if [[ ! -f "$PID_FILE" && ! -L "$PID_FILE" ]]; then
  echo "No latest PID file found: $PID_FILE"
  echo "Manual check:"
  echo "  ps -u \$USER -f | grep -E 'run_train|train_rllib_sac.py|eval_rllib_checkpoint.py|ray|gotsc' | grep -v grep"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ -z "$PID" ]]; then
  echo "PID file is empty: $PID_FILE"
  exit 1
fi

echo "Stopping train/eval process group: $PID"

if kill -0 "-$PID" 2>/dev/null; then
  kill "-$PID" || true
  sleep 8
elif kill -0 "$PID" 2>/dev/null; then
  kill "$PID" || true
  sleep 8
else
  echo "Process $PID is not running."
fi

if kill -0 "-$PID" 2>/dev/null; then
  echo "Process group still alive. Sending SIGKILL..."
  kill -9 "-$PID" || true
elif kill -0 "$PID" 2>/dev/null; then
  echo "Process still alive. Sending SIGKILL..."
  kill -9 "$PID" || true
fi

echo "Stopping Ray..."
ray stop --force >/dev/null 2>&1 || true

echo "Done."
