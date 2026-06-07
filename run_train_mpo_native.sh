#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(dirname "$PROJECT_DIR")}"

CONFIG=${1:-configs/mpo_b89_physics_blended_raw_recurrent_192worker_1m_probe.json}
OVERRIDE=${2:-}

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# Keep one TSC/Ray worker from spawning many numerical threads.
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

# Short Ray temp path avoids AF_UNIX socket path limit.
export RAY_TMPDIR=${RAY_TMPDIR:-/tmp/rm$(id -u)}
export TMPDIR=${TMPDIR:-${RAY_TMPDIR}/tmp}
mkdir -p "$RAY_TMPDIR" "$TMPDIR" logs

ulimit -n 4096 || true
cur_u=$(ulimit -u || echo 0)
if [[ "$cur_u" != "unlimited" ]]; then
  if [[ "$cur_u" -lt 30000 ]]; then
    ulimit -u 30000 || true
  fi
fi

CMD=(python scripts/train_mpo.py --config "$CONFIG")
if [[ -n "$OVERRIDE" ]]; then
  CMD+=(--override "$OVERRIDE")
fi

echo "[run_train_mpo_native] CONFIG=$CONFIG"
echo "[run_train_mpo_native] RAY_TMPDIR=$RAY_TMPDIR"
echo "[run_train_mpo_native] CMD=${CMD[*]}"
exec "${CMD[@]}"
