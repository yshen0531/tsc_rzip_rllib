#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b87_shape_first_relaxed_ip_recurrent_192worker_1m_probe.json}"
RUN_DIR="${2:-mpo_checkpoints/train_b87_shape_first_relaxed_ip_mpo_192worker_1m_probe_YYYYMMDD_HHMMSS}"
OUT_DIR="${3:-eval_results}"
mkdir -p "$OUT_DIR"

for ck in 000025 000050 000075 000100 000125 000150; do
  CKPT="$RUN_DIR/iter_${ck}"
  if [[ -f "$CKPT/mpo_checkpoint.pt" ]]; then
    ./run_eval_mpo_policy.sh \
      "$CONFIG" \
      "$CKPT" \
      "$OUT_DIR/b87_iter_${ck}_final_det.csv" \
      final deterministic 1
  else
    echo "[skip] missing $CKPT/mpo_checkpoint.pt"
  fi
done
