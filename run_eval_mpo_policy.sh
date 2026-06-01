#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(dirname "$PROJECT_DIR")}"

CONFIG=${1:-configs/mpo_b85_recurrent_192worker_5m.json}
CHECKPOINT=${2:?"checkpoint dir required, e.g. mpo_checkpoints/<run>/final"}
OUT=${3:-eval_results/mpo_eval.csv}
STAGE=${4:-final}
MODE=${5:-deterministic}
EPISODES=${6:-5}

export PYTHONPATH="$PWD:${PYTHONPATH:-}"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}
export TORCH_NUM_THREADS=${TORCH_NUM_THREADS:-1}
export TORCH_NUM_INTEROP_THREADS=${TORCH_NUM_INTEROP_THREADS:-1}

python scripts/eval_mpo_policy.py \
  --config "$CONFIG" \
  --checkpoint "$CHECKPOINT" \
  --episodes "$EPISODES" \
  --out "$OUT" \
  --eval-stage "$STAGE" \
  --action-mode "$MODE"
