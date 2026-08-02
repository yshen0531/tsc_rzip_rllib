#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$PROJECT_ROOT/logs/nohup/latest_stage4_2r3c3t13s17.pid"
if [[ ! -f "$PID_FILE" ]]; then
  printf 'No T13S17 PID file.\n'
  exit 0
fi
PID="$(cat "$PID_FILE")"
case "$PID" in
  ''|*[!0-9]*) printf 'Invalid T13S17 PID: %s\n' "$PID" >&2; exit 1 ;;
esac
if kill -0 "$PID" 2>/dev/null; then
  CMDLINE="$(tr '\0' ' ' <"/proc/$PID/cmdline" 2>/dev/null || true)"
  case "$CMDLINE" in
    *stage4_2r3c3t13s17*) kill "$PID"; printf 'Stopped T13S17 PID %s\n' "$PID" ;;
    *) printf 'PID %s is not the T13S17 process; refusing to stop.\n' "$PID" >&2; exit 1 ;;
  esac
else
  printf 'T13S17 PID %s is not running.\n' "$PID"
fi
