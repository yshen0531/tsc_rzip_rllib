#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Raise soft limits when the hard limits allow it.
ulimit -u 65535 || true
ulimit -n 4096 || true

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# Short Ray tmp path. Avoid AF_UNIX socket path length issues.
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/ry_${USER}}"
export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR"
mkdir -p "$RAY_TMPDIR" "$TMPDIR"

# Prevent every Ray worker / PyTorch / BLAS from spawning many threads.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1
export RAYON_NUM_THREADS=1
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0

echo "========== limits =========="
ulimit -u
ulimit -n
echo "threads before:"
ps -u "$USER" -L --no-headers | wc -l
echo "processes before:"
ps -u "$USER" --no-headers | wc -l
echo "============================"

python scripts/train_rllib_sac.py \
  --config configs/rllib_sac.json \
  --override "${1:-configs/train_b81_96worker_100k.json}"
