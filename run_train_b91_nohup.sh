#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b91_rguard_split_vertical_recurrent_192worker_1p8m_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b91_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b91.log

echo "[run_train_b91_nohup] log=${log}"
nohup ./run_train_b91_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b91_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b91_nohup] tail -f ${log}"
