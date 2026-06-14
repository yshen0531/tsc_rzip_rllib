#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b92_resume_from_b91_iter375_to_2p8m_recurrent_192worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b92_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b92_train.log

nohup ./run_train_b92_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b92_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b92_nohup] tail -f ${log}"
