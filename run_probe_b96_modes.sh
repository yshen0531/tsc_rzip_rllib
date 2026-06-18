#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b96_resume_from_b93_iter500_to_3p5m_recurrent_192worker_probe.json}"
OUT="${2:-eval_results/b96_mode_sign_probe_stage3.csv}"
STAGE="${3:-final}"
STEPS="${4:-80}"
AMP="${5:-0.35}"

cd "$(dirname "$0")"
mkdir -p "$(dirname "${OUT}")"
python scripts/probe_mpo_action_modes.py \
  --config "${CONFIG}" \
  --out "${OUT}" \
  --eval-stage "${STAGE}" \
  --steps "${STEPS}" \
  --amplitude "${AMP}"
