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

CONFIG=${1:?Usage: $0 CONFIG CHECKPOINT OUT_CSV [eval_stage] [action_mode] [episodes] [override_json]}
CHECKPOINT=${2:?Usage: $0 CONFIG CHECKPOINT OUT_CSV [eval_stage] [action_mode] [episodes] [override_json]}
OUT=${3:?Usage: $0 CONFIG CHECKPOINT OUT_CSV [eval_stage] [action_mode] [episodes] [override_json]}
EVAL_STAGE=${4:-final}
ACTION_MODE=${5:-deterministic}
EPISODES=${6:-1}
OVERRIDE=${7:-}

CMD=(python scripts/eval_mpo_policy.py --config "$CONFIG" --checkpoint "$CHECKPOINT" --out "$OUT" --eval-stage "$EVAL_STAGE" --action-mode "$ACTION_MODE" --episodes "$EPISODES")
if [[ -n "$OVERRIDE" ]]; then
  CMD+=(--override "$OVERRIDE")
fi

echo "[run_eval_mpo_policy] CMD=${CMD[*]}"
exec "${CMD[@]}"
