#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b98_resume_from_b97_iter575_to_4p2m_recurrent_192worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b98_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b98_train.log

nohup ./run_train_b98_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b98_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b98_nohup] tail -f ${log}"
