#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b93_resume_from_b92_iter450_to_3p1m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b92_rprogress_commonmode_from_b91_iter375_mpo_192worker_probe_20260614_233859/iter_000450}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b93_from_b92_iter450] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument. Default intentionally uses iter_000450, not final/." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b93_from_b92_iter450_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b93_resume.log

echo "[run_resume_b93_from_b92_iter450] CONFIG=${CONFIG}"
echo "[run_resume_b93_from_b92_iter450] RESUME=${RESUME}"
echo "[run_resume_b93_from_b92_iter450] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b93_from_b92_iter450] log=${log}"
nohup ./run_train_b93_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b93_from_b92_iter450] pid=$(cat "${log}.pid")"
echo "[run_resume_b93_from_b92_iter450] tail -f ${log}"
