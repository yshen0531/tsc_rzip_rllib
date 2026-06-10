#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b91_resume_from_b90_1p8m_to_2p4m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b90_resume_to_1p8m_from_iter200_split_vertical_posz_mpo_192worker_probe_20260609_183139/final}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b91_from_b90_1p8m] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument (for example the final/ or iter_000275 directory)." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b91_from_b90_1p8m_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b91_resume.log

echo "[run_resume_b91_from_b90_1p8m] CONFIG=${CONFIG}"
echo "[run_resume_b91_from_b90_1p8m] RESUME=${RESUME}"
echo "[run_resume_b91_from_b90_1p8m] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b91_from_b90_1p8m] log=${log}"
nohup ./run_train_b91_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b91_from_b90_1p8m] pid=$(cat "${log}.pid")"
echo "[run_resume_b91_from_b90_1p8m] tail -f ${log}"
