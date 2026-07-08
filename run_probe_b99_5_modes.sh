#!/usr/bin/env bash
set -euo pipefail
python -u scripts/probe_mpo_action_modes.py \
  --config configs/mpo_b99_5_terminal_late_cost_runtime_only_10ms_extrema_192worker.json \
  --checkpoint mpo_checkpoints/train_b99_5_terminal_late_cost_runtime_only_10ms_extrema_from_scratch_mpo_192worker/final
