#!/usr/bin/env bash
set -euo pipefail
CONFIG="configs/mpo_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_192worker.json"
CKPT="${1:-}"
if [[ -z "$CKPT" ]]; then
  echo "Usage: $0 /path/to/checkpoint" >&2
  exit 2
fi
python -u scripts/probe_mpo_action_modes.py --config "$CONFIG" --checkpoint "$CKPT"
