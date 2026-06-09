#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(dirname "$PROJECT_DIR")}" 
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}
export TORCH_NUM_THREADS=${TORCH_NUM_THREADS:-1}
export TORCH_NUM_INTEROP_THREADS=${TORCH_NUM_INTEROP_THREADS:-1}

CONFIG=${1:-configs/mpo_b90_split_vertical_posz_recurrent_192worker_1p5m_probe.json}
OUT=${2:-eval_results/b90_mode_sign_probe_stage0.csv}
STAGE=${3:-stage0}
STEPS=${4:-80}
ACTION_SCALE=${5:-0.35}

python scripts/probe_mpo_action_modes.py \
  --config "$CONFIG" \
  --out "$OUT" \
  --eval-stage "$STAGE" \
  --steps "$STEPS" \
  --action-scale "$ACTION_SCALE"
