#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Train phase must not inherit eval Ray tmp settings from an interactive shell.
export RAY_TMPDIR="/tmp/ry_${USER}"
export TMPDIR="${RAY_TMPDIR}/tmp"

CONFIG="${1:-configs/train_b82_96worker_2m.json}"
EVAL_EPISODES="${EVAL_EPISODES:-5}"
EVAL_MAX_STEPS="${EVAL_MAX_STEPS:-0}"
STAMP="$(date +%Y%m%d_%H%M%S)"

# Helper: merge rllib_sac.json with override and print run_name.
RUN_NAME="$(python - "$CONFIG" <<'PY'
import json, sys
from pathlib import Path

def deep_update(a,b):
    out=dict(a)
    for k,v in b.items():
        if isinstance(v,dict) and isinstance(out.get(k),dict):
            out[k]=deep_update(out[k],v)
        else:
            out[k]=v
    return out
base=json.load(open('configs/rllib_sac.json',encoding='utf-8'))
ov_path=Path(sys.argv[1])
ov=json.load(open(ov_path,encoding='utf-8')) if ov_path.exists() else {}
print(deep_update(base,ov).get('run_name','rllib_sac_tsc_rzip'))
PY
)"

echo "========== train+eval =========="
echo "CONFIG        = $CONFIG"
echo "RUN_NAME      = $RUN_NAME"
echo "EVAL_EPISODES = $EVAL_EPISODES"
echo "STAMP         = $STAMP"
echo "================================"

bash run_train_native.sh "$CONFIG"

RUN_DIR="$(ls -td ray_results/${RUN_NAME}_* 2>/dev/null | head -1 || true)"
CKPT="$(ls -td ray_checkpoints/${RUN_NAME}_*/final 2>/dev/null | head -1 || true)"

if [[ -z "$RUN_DIR" || -z "$CKPT" ]]; then
  echo "ERROR: Could not locate latest run dir or final checkpoint for RUN_NAME=$RUN_NAME" >&2
  echo "RUN_DIR=$RUN_DIR" >&2
  echo "CKPT=$CKPT" >&2
  exit 2
fi

echo "Latest run dir:     $RUN_DIR"
echo "Final checkpoint:   $CKPT"

echo "========== analyze train run =========="
python scripts/analyze_rllib_run.py "$RUN_DIR" | tee "$RUN_DIR/analyze_rllib_run.txt"

echo "========== eval final checkpoint =========="
ray stop --force >/dev/null 2>&1 || true
export RAY_TMPDIR="/tmp/ry_eval_${USER}"
export TMPDIR="${RAY_TMPDIR}/tmp"
rm -rf "$RAY_TMPDIR"
mkdir -p "$TMPDIR" eval_results

EVAL_OUT="eval_results/${RUN_NAME}_${STAMP}_final_eval.csv"
EVAL_CMD=(python scripts/eval_rllib_checkpoint.py --config configs/rllib_sac.json --override "$CONFIG" --checkpoint "$CKPT" --episodes "$EVAL_EPISODES" --out "$EVAL_OUT")
if [[ "$EVAL_MAX_STEPS" != "0" ]]; then
  EVAL_CMD+=(--max-steps "$EVAL_MAX_STEPS")
fi
"${EVAL_CMD[@]}"

echo "========== done =========="
echo "Run dir:    $RUN_DIR"
echo "Checkpoint: $CKPT"
echo "Eval CSV:   $EVAL_OUT"
echo "Eval JSON:  ${EVAL_OUT%.csv}.summary.json"
