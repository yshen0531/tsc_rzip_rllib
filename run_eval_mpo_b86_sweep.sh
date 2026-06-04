#!/usr/bin/env bash
set -euo pipefail
CONFIG=${1:-configs/mpo_b86_balanced_recurrent_192worker_1m_probe.json}
RUN_NAME=${2:?run name required, e.g. train_b86_balanced_recurrent_mpo_192worker_1m_probe_YYYYMMDD_HHMMSS}
STAGE=${3:-final}
MODE=${4:-deterministic}
EPISODES=${5:-1}
CKPTS=${6:-"000025 000050 000075 000100 000125 000150"}

mkdir -p eval_results
for ck in $CKPTS; do
  CKPT_DIR="mpo_checkpoints/${RUN_NAME}/iter_${ck}"
  if [[ ! -f "${CKPT_DIR}/mpo_checkpoint.pt" ]]; then
    echo "[skip] missing ${CKPT_DIR}/mpo_checkpoint.pt"
    continue
  fi
  OUT="eval_results/${RUN_NAME}_iter_${ck}_${STAGE}_${MODE}.csv"
  ./run_eval_mpo_policy.sh "$CONFIG" "$CKPT_DIR" "$OUT" "$STAGE" "$MODE" "$EPISODES"
done
