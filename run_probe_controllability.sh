#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# One Python/TSC probe worker should not spawn many numerical threads.
# This is critical when --num-workers > 1.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1
export RAYON_NUM_THREADS=1
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0

echo "========== probe thread limits =========="
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "NUMEXPR_NUM_THREADS=$NUMEXPR_NUM_THREADS"
echo "TORCH_NUM_THREADS=$TORCH_NUM_THREADS"
echo "BLIS_NUM_THREADS=$BLIS_NUM_THREADS"
echo "========================================="

python scripts/probe_controllability.py "$@"