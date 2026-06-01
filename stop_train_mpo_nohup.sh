#!/usr/bin/env bash
set -u
PID_FILE="logs/pids/latest_train_mpo.pid"
if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "SIGTERM main MPO pid=$pid"
    kill -TERM "$pid" 2>/dev/null || true
  fi
else
  echo "No pid file: $PID_FILE"
fi

pkill -TERM -u "$USER" -f "scripts/train_mpo.py" 2>/dev/null || true
sleep 5
left=$(pgrep -u "$USER" -af "scripts/train_mpo.py" || true)
if [[ -n "$left" ]]; then
  echo "Remaining train_mpo processes:"
  echo "$left"
  pkill -KILL -u "$USER" -f "scripts/train_mpo.py" 2>/dev/null || true
fi
rm -f "$PID_FILE" 2>/dev/null || true
echo "done"
