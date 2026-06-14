#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b92_resume_from_b91_iter375_to_2p8m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b91_rguard_from_b90_1p8m_split_vertical_mpo_192worker_probe_20260614_004723/iter_000375}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b92_from_b91_iter375] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument. Default intentionally uses iter_000375, not final/." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b92_from_b91_iter375_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b92_resume.log

echo "[run_resume_b92_from_b91_iter375] CONFIG=${CONFIG}"
echo "[run_resume_b92_from_b91_iter375] RESUME=${RESUME}"
echo "[run_resume_b92_from_b91_iter375] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b92_from_b91_iter375] log=${log}"
nohup ./run_train_b92_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b92_from_b91_iter375] pid=$(cat "${log}.pid")"
echo "[run_resume_b92_from_b91_iter375] tail -f ${log}"
