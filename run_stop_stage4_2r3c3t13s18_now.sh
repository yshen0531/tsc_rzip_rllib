#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s18.pid"
if [[ ! -f "$PID_FILE" ]]; then
  printf 'No T13S18 PID file.\n'
  exit 0
fi
PID="$(cat "$PID_FILE")"
if [[ ! "$PID" =~ ^[0-9]+$ ]]; then
  printf 'Invalid T13S18 PID: %s\n' "$PID" >&2
  exit 1
fi
if kill -0 "$PID" 2>/dev/null; then
  COMMAND="$(ps -p "$PID" -o args=)"
  if [[ "$COMMAND" != *"run_stage4_2r3c3t13s18_all.sh"* ]]; then
    printf 'Refusing to stop unrelated PID %s: %s\n' "$PID" "$COMMAND" >&2
    exit 1
  fi
  kill "$PID"
  printf 'Stopped T13S18 PID %s.\n' "$PID"
else
  printf 'T13S18 PID %s is not running.\n' "$PID"
fi
