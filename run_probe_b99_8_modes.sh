#!/usr/bin/env bash
set -euo pipefail
CONFIG="configs/mpo_b99_8_resume_b99_6_best_error_actor_guard_ip_relaxed_runtime_only_192worker.json"
DEFAULT_CKPT="$(ls -dt mpo_checkpoints/train_b99_8_resume_b99_6_best_error_actor_guard_ip_relaxed_runtime_only_mpo_192worker_*/best_error_score 2>/dev/null | head -1 || true)"
B99_8_PROBE_CKPT="${B99_8_PROBE_CKPT:-$DEFAULT_CKPT}"
if [[ -z "$B99_8_PROBE_CKPT" || ! -f "$B99_8_PROBE_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[run_probe_b99_8_modes] ERROR: checkpoint not found. Set B99_8_PROBE_CKPT=/path/to/checkpoint_dir" >&2
  exit 2
fi
python -u scripts/probe_mpo_action_modes.py \
  --config "$CONFIG" \
  --checkpoint "$B99_8_PROBE_CKPT"
