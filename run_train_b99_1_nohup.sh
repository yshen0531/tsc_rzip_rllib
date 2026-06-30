#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b99_1_constrained_goal_10ms_128worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"
mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/train_b99_1_10ms_from_scratch_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b99_1_train.log

echo "[run_train_b99_1_nohup] CONFIG=${CONFIG}"
echo "[run_train_b99_1_nohup] OVERRIDE=${OVERRIDE}"
echo "[run_train_b99_1_nohup] RESUME=${RESUME}"
echo "[run_train_b99_1_nohup] log=${log}"
nohup ./run_train_b99_1_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_train_b99_1_nohup] pid=$(cat "${log}.pid")"
echo "[run_train_b99_1_nohup] tail -f ${log}"
