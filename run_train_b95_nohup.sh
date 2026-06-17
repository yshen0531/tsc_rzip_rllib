#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b95_resume_from_b93_iter500_to_3p5m_recurrent_192worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b95_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b95_train.log

nohup ./run_train_b95_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b95_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b95_nohup] tail -f ${log}"
