#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CONFIG="${1:-configs/mpo_b99_constrained_goal_from_scratch_192worker_probe.json}"
OUT="${2:-eval_results/b99_mode_sign_probe_stage0.csv}"
STAGE="${3:-stage0}"
STEPS="${4:-80}"
ACTION_SCALE="${5:-0.35}"
python -u scripts/probe_mpo_action_modes.py --config "$CONFIG" --out "$OUT" --eval-stage "$STAGE" --steps "$STEPS" --action-scale "$ACTION_SCALE"
