#!/usr/bin/env bash
set -euo pipefail
CONFIG="configs/mpo_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_192worker.json"
DEFAULT_CKPT="mpo_checkpoints/train_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_mpo_192worker/best_error_score"
B99_6_PROBE_CKPT="${B99_6_PROBE_CKPT:-$DEFAULT_CKPT}"
python -u scripts/probe_mpo_action_modes.py \
  --config "$CONFIG" \
  --checkpoint "$B99_6_PROBE_CKPT"
