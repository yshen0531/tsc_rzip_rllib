#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
PID_FILE="logs/pids/latest_probe.pid"

if [[ ! -f "$PID_FILE" && ! -L "$PID_FILE" ]]; then
  echo "No latest probe PID file found: $PID_FILE"
  echo "Manual check: ps -u \$USER -f | grep -E 'probe_controllability.py|gotsc' | grep -v grep"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if [[ -z "$PID" ]]; then
  echo "PID file is empty: $PID_FILE"
  exit 1
fi

echo "Stopping controllability probe process group: $PID"
if kill -0 "-$PID" 2>/dev/null; then
  kill "-$PID" || true
  sleep 5
elif kill -0 "$PID" 2>/dev/null; then
  kill "$PID" || true
  sleep 5
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

echo "Done."
