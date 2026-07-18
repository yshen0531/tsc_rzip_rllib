#!/usr/bin/env bash
set -u
PID_FILE="stage1_1_runs/stage1_1_driver.pid"
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$PID" ]]; then
    PGID="$(ps -o pgid= -p "$PID" 2>/dev/null | tr -d ' ' || true)"
    if [[ -n "$PGID" ]]; then
      kill -KILL -- "-$PGID" 2>/dev/null || true
    fi
    kill -KILL "$PID" 2>/dev/null || true
  fi
fi
pkill -KILL -f 'scripts/stage1_1_supplement.py' 2>/dev/null || true
ray stop --force >/dev/null 2>&1 || true
echo "[Stage1.1] immediate stop requested. Completed raw/validation JSON files are retained."
