#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b93_resume_from_b92_iter450_to_3p1m_recurrent_192worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b93_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b93_train.log

nohup ./run_train_b93_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b93_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b93_nohup] tail -f ${log}"
