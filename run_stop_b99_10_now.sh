#!/usr/bin/env bash
set -euo pipefail
PIDFILE="logs/nohup/latest_b99_10_resume_b99_9_train_first_train.pid"
if [[ ! -f "$PIDFILE" ]]; then
  echo "[B99.10 stop] PID file not found: $PIDFILE" >&2
  exit 2
fi
PID="$(cat "$PIDFILE")"
echo "[B99.10 stop] immediately killing process group -$PID"
kill -KILL -- "-$PID" 2>/dev/null || kill -KILL "$PID" 2>/dev/null || true
ray stop --force >/dev/null 2>&1 || true
rm -f "$PIDFILE"
echo "[B99.10 stop] stopped. No graceful final checkpoint/eval was attempted."
