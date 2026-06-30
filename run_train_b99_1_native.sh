#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/mpo_b99_1_constrained_goal_10ms_128worker_probe.json}"
OVERRIDE="${2:-}"
RESUME="${3:-}"

cd "$(dirname "$0")"

echo "[run_train_b99_1_native] limit before set: ulimit -u=$(ulimit -u) ulimit -n=$(ulimit -n)"
ulimit -u 30000 || true
ulimit -n 65535 || ulimit -n 4096 || true
echo "[run_train_b99_1_native] limit after set : ulimit -u=$(ulimit -u) ulimit -n=$(ulimit -n)"
cat /proc/$$/limits | egrep "processes|open files" || true

if [[ -n "${RESUME}" ]]; then
  if [[ ! -f "${RESUME}/mpo_checkpoint.pt" ]]; then
    echo "[run_train_b99_1_native] ERROR: resume checkpoint not found: ${RESUME}/mpo_checkpoint.pt" >&2
    exit 2
  fi
fi

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}
export TORCH_NUM_THREADS=${TORCH_NUM_THREADS:-1}
export TORCH_NUM_INTEROP_THREADS=${TORCH_NUM_INTEROP_THREADS:-1}
export VECLIB_MAXIMUM_THREADS=${VECLIB_MAXIMUM_THREADS:-1}
export BLIS_NUM_THREADS=${BLIS_NUM_THREADS:-1}
export RAYON_NUM_THREADS=${RAYON_NUM_THREADS:-1}
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=${RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO:-0}

if [[ -z "${RAY_TMPDIR:-}" ]]; then
  export RAY_TMPDIR="/tmp/ray_${USER}_b991_${RANDOM}"
fi
mkdir -p "${RAY_TMPDIR}"

cmd=(python -u scripts/train_mpo.py --config "${CONFIG}")
if [[ -n "${OVERRIDE}" ]]; then
  cmd+=(--override "${OVERRIDE}")
fi
if [[ -n "${RESUME}" ]]; then
  cmd+=(--resume "${RESUME}")
fi

echo "[run_train_b99_1_native] CONFIG=${CONFIG}"
echo "[run_train_b99_1_native] OVERRIDE=${OVERRIDE}"
echo "[run_train_b99_1_native] RESUME=${RESUME}"
echo "[run_train_b99_1_native] RAY_TMPDIR=${RAY_TMPDIR}"
echo "[run_train_b99_1_native] CMD=${cmd[*]}"
exec "${cmd[@]}"
