#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b96_resume_from_b95_iter550_to_3p9m_recurrent_192worker_probe.json}"
RESUME="${2:-mpo_checkpoints/train_b95_target_curriculum_from_b93_iter500_mpo_192worker_probe_20260616_140102/iter_000550}"
OVERRIDE="${3:-}"

cd "$(dirname "$0")"

if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
  echo "[run_resume_b96_from_b95_iter550] ERROR: checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
  echo "Pass explicit checkpoint dir as the second argument. Default intentionally uses iter_000550, not final/." >&2
  exit 2
fi

mkdir -p logs/nohup
stamp=$(date +%Y%m%d_%H%M%S)
log="logs/nohup/resume_b96_from_b95_iter550_${stamp}.log"
ln -sfn "$(basename "$log")" logs/nohup/latest_b96_resume.log

echo "[run_resume_b96_from_b95_iter550] CONFIG=${CONFIG}"
echo "[run_resume_b96_from_b95_iter550] RESUME=${RESUME}"
echo "[run_resume_b96_from_b95_iter550] OVERRIDE=${OVERRIDE}"
echo "[run_resume_b96_from_b95_iter550] log=${log}"
nohup ./run_train_b96_native.sh "${CONFIG}" "${OVERRIDE}" "${RESUME}" > "${log}" 2>&1 &
echo $! > "${log}.pid"
echo "[run_resume_b96_from_b95_iter550] pid=$(cat "${log}.pid")"
echo "[run_resume_b96_from_b95_iter550] tail -f ${log}"
