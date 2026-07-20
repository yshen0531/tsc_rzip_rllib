#!/usr/bin/env bash
set -u
PID_FILE="stage2_runs/stage2_driver.pid"
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
pkill -KILL -f 'scripts/stage2_trajectory_optimization.py' 2>/dev/null || true
ray stop --force >/dev/null 2>&1 || true
WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-/tmp/tsc_workspace/episode_runs}"
find "$WORKSPACE_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'stage2_*' -exec rm -rf -- {} + 2>/dev/null || true
rm -rf "$RUN_ROOT"/* 2>/dev/null || true
echo "[Stage2] stopped and temporary TSC directories were removed."
