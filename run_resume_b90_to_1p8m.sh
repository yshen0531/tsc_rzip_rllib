#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

CONFIG=${1:-configs/mpo_b90_resume_to_1p8m_recurrent_192worker_probe.json}
RESUME=${2:-mpo_checkpoints/train_b90_split_vertical_posz_mpo_192worker_1p5m_probe_20260607_225834/iter_000200}
OVERRIDE=${3:-}

if [[ ! -f "$CONFIG" ]]; then
  echo "ERROR: config not found: $CONFIG" >&2
  exit 2
fi
if [[ ! -f "$RESUME/mpo_checkpoint.pt" ]]; then
  echo "ERROR: resume checkpoint not found: $RESUME/mpo_checkpoint.pt" >&2
  echo "Pass the checkpoint directory as the second argument, e.g." >&2
  echo "  ./run_resume_b90_to_1p8m.sh $CONFIG mpo_checkpoints/<B90_RUN>/iter_000200" >&2
  exit 2
fi
if [[ -n "$OVERRIDE" && ! -f "$OVERRIDE" ]]; then
  echo "ERROR: override JSON not found: $OVERRIDE" >&2
  exit 2
fi

STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p logs/nohup logs/pids
LOG="logs/nohup/resume_b90_to_1p8m_${STAMP}.log"
ln -sfn "$(basename "$LOG")" logs/nohup/latest_mpo.log

if [[ -n "$OVERRIDE" ]]; then
  nohup bash run_train_mpo_native.sh "$CONFIG" "$OVERRIDE" "$RESUME" > "$LOG" 2>&1 &
else
  nohup bash run_train_mpo_native.sh "$CONFIG" "" "$RESUME" > "$LOG" 2>&1 &
fi
PID=$!
echo "$PID" > logs/pids/latest_train_mpo.pid

echo "Started B90 resume-to-1.8M training. pid=$PID"
echo "Config: $CONFIG"
echo "Resume: $RESUME"
echo "Log: $LOG"
echo "Follow: tail -f logs/nohup/latest_mpo.log"
