#!/usr/bin/env bash
set -u
# B85-stable root-safe stop script.  It targets the owner of this checkout,
# not necessarily the current shell user (useful when logged in as root).
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OWNER="${MPO_OWNER:-$(stat -c %U "$PROJECT_DIR" 2>/dev/null || echo "${SUDO_USER:-$USER}")}"
PID_FILE="$PROJECT_DIR/logs/pids/latest_train_mpo.pid"

echo "[stop_train_mpo_nohup] PROJECT_DIR=$PROJECT_DIR"
echo "[stop_train_mpo_nohup] OWNER=$OWNER"

if [[ -f "$PID_FILE" ]]; then
  pid=$(cat "$PID_FILE" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "SIGTERM main MPO pid=$pid"
    kill -TERM "$pid" 2>/dev/null || true
  fi
else
  echo "No pid file: $PID_FILE"
fi

# Match both old B85 and stable B85 commands, but only for the project owner.
pkill -TERM -u "$OWNER" -f "$PROJECT_DIR/scripts/train_mpo.py" 2>/dev/null || true
pkill -TERM -u "$OWNER" -f "run_train_mpo" 2>/dev/null || true
sleep 12

left=$(pgrep -u "$OWNER" -af "train_mpo.py|run_train_mpo" || true)
if [[ -n "$left" ]]; then
  echo "Remaining train_mpo processes after SIGTERM:"
  echo "$left"
  echo "Escalating to SIGKILL for train_mpo only."
  pkill -KILL -u "$OWNER" -f "$PROJECT_DIR/scripts/train_mpo.py" 2>/dev/null || true
  pkill -KILL -u "$OWNER" -f "run_train_mpo" 2>/dev/null || true
fi

rm -f "$PID_FILE" 2>/dev/null || true

echo "Remaining Ray/TSC processes for $OWNER:"
pgrep -u "$OWNER" -af "raylet|gcs_server|gotsc|dashboard|runtime_env" || true

echo "done"
