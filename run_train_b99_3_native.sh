#!/usr/bin/env bash
set -euo pipefail

ulimit -u 262144 || true
ulimit -n 1048576 || true

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1
export RAYON_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export TORCH_NUM_INTEROP_THREADS=1
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0

export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/rm$(id -u)}"
mkdir -p "$RAY_TMPDIR" "$RAY_TMPDIR/tmp"
export TMPDIR="$RAY_TMPDIR/tmp"

# Keep old Ray sessions from stealing file descriptors / CPUs if this is a fresh run.
ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

echo "[run_train_b99_3_native] user=$(whoami) host=$(hostname) pwd=$(pwd)"
echo "[run_train_b99_3_native] ulimit -n=$(ulimit -n) ulimit -u=$(ulimit -u)"
echo "[run_train_b99_3_native] RAY_TMPDIR=$RAY_TMPDIR"
echo "[run_train_b99_3_native] nproc=$(nproc) nproc_all=$(nproc --all)"
grep Cpus_allowed_list /proc/self/status || true
taskset -pc $$ || true
echo "[run_train_b99_3_native] SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-unset}"
echo "[run_train_b99_3_native] config=configs/mpo_b99_3_fast_runtime_only_10ms_extrema_224worker.json"

python -u scripts/train_mpo.py \
  --config configs/mpo_b99_3_fast_runtime_only_10ms_extrema_224worker.json
