#!/usr/bin/env bash
set -u

PID_FILE="logs/pids/latest_eval_sweep.pid"

echo "[stop] stopping checkpoint sweep ..."

if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
        echo "[stop] SIGTERM main sweep pid=$pid"
        kill -TERM "$pid" 2>/dev/null || true
    else
        echo "[stop] pid file exists but process is not alive: ${pid:-empty}"
    fi
else
    echo "[stop] no pid file: $PID_FILE"
fi

echo "[stop] SIGTERM matching eval/ray/gotsc processes ..."
pkill -TERM -u "$USER" -f "eval_checkpoint_sweep.py" 2>/dev/null || true
pkill -TERM -u "$USER" -f "eval_rllib_checkpoint.py" 2>/dev/null || true
pkill -TERM -u "$USER" -f "run_eval_checkpoint_sweep" 2>/dev/null || true
pkill -TERM -u "$USER" -f "raylet" 2>/dev/null || true
pkill -TERM -u "$USER" -f "gcs_server" 2>/dev/null || true
pkill -TERM -u "$USER" -f "gotsc" 2>/dev/null || true

sleep 5

left="$(pgrep -u "$USER" -af "eval_checkpoint_sweep.py|eval_rllib_checkpoint.py|run_eval_checkpoint_sweep|raylet|gcs_server|gotsc" || true)"
if [[ -n "$left" ]]; then
    echo "[stop] remaining processes after SIGTERM:"
    echo "$left" | head -80

    echo "[stop] sending SIGKILL to remaining matching processes ..."
    pkill -KILL -u "$USER" -f "eval_checkpoint_sweep.py" 2>/dev/null || true
    pkill -KILL -u "$USER" -f "eval_rllib_checkpoint.py" 2>/dev/null || true
    pkill -KILL -u "$USER" -f "run_eval_checkpoint_sweep" 2>/dev/null || true
    pkill -KILL -u "$USER" -f "raylet" 2>/dev/null || true
    pkill -KILL -u "$USER" -f "gcs_server" 2>/dev/null || true
    pkill -KILL -u "$USER" -f "gotsc" 2>/dev/null || true
else
    echo "[stop] no matching processes remain after SIGTERM."
fi

rm -f "$PID_FILE" 2>/dev/null || true

echo "[stop] cleanup tmp dirs ..."
rm -rf "/tmp/ry_eval_sweep_${USER}" 2>/dev/null || true
rm -rf "/tmp/rs$(id -u)" 2>/dev/null || true

echo "[stop] done."