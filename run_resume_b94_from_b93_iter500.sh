#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b94_resume_from_b93_iter500_to_3p35m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b93_actor_limited_modes_from_b92_iter450_mpo_192worker_probe_20260615_135541/iter_000500}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b94_from_b93_iter500] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument. Default intentionally uses iter_000500, not final/." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b94_from_b93_iter500_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b94_resume.log

echo "[run_resume_b94_from_b93_iter500] CONFIG=${CONFIG}"
echo "[run_resume_b94_from_b93_iter500] RESUME=${RESUME}"
echo "[run_resume_b94_from_b93_iter500] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b94_from_b93_iter500] log=${log}"
nohup ./run_train_b94_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b94_from_b93_iter500] pid=$(cat "${log}.pid")"
echo "[run_resume_b94_from_b93_iter500] tail -f ${log}"
