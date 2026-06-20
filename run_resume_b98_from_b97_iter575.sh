#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b98_resume_from_b97_iter575_to_4p2m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b97_fixed_core_goal_ready_from_b95_iter550_mpo_192worker_probe_20260618_103020/iter_000575}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b98_from_b97_iter575] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument. Default intentionally uses iter_000575, not final/." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b98_from_b97_iter575_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b98_resume.log

echo "[run_resume_b98_from_b97_iter575] CONFIG=${CONFIG}"
echo "[run_resume_b98_from_b97_iter575] RESUME=${RESUME}"
echo "[run_resume_b98_from_b97_iter575] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b98_from_b97_iter575] log=${log}"
nohup ./run_train_b98_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b98_from_b97_iter575] pid=$(cat "${log}.pid")"
echo "[run_resume_b98_from_b97_iter575] tail -f ${log}"
