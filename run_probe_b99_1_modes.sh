#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
CONFIG="${1:-configs/mpo_b99_1_constrained_goal_10ms_128worker_probe.json}"
OUT="${2:-eval_results/b99_1_mode_sign_probe_stage0.csv}"
STAGE="${3:-stage0}"
STEPS="${4:-65}"
ACTION_SCALE="${5:-0.35}"
python -u scripts/probe_mpo_action_modes.py --config "$CONFIG" --out "$OUT" --eval-stage "$STAGE" --steps "$STEPS" --action-scale "$ACTION_SCALE"
