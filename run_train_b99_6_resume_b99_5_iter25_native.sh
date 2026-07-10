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

# Fresh Ray session for this resume run.
ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

CONFIG="configs/mpo_b99_6_resume_b99_5_iter25_actor_slow_ip_tight_runtime_only_192worker.json"
DEFAULT_CKPT="mpo_checkpoints/train_b99_5_terminal_late_cost_runtime_only_10ms_extrema_from_scratch_mpo_192worker/iter_000025"
B99_5_RESUME_CKPT="${B99_5_RESUME_CKPT:-$DEFAULT_CKPT}"

if [[ ! -f "$B99_5_RESUME_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[run_train_b99_6_resume_b99_5_iter25_native] ERROR: resume checkpoint not found:" >&2
  echo "  $B99_5_RESUME_CKPT/mpo_checkpoint.pt" >&2
  echo "Set B99_5_RESUME_CKPT=/path/to/iter_000025 if your checkpoint is elsewhere." >&2
  exit 2
fi

echo "[run_train_b99_6_resume_b99_5_iter25_native] user=$(whoami) host=$(hostname) pwd=$(pwd)"
echo "[run_train_b99_6_resume_b99_5_iter25_native] ulimit -n=$(ulimit -n) ulimit -u=$(ulimit -u)"
echo "[run_train_b99_6_resume_b99_5_iter25_native] RAY_TMPDIR=$RAY_TMPDIR"
echo "[run_train_b99_6_resume_b99_5_iter25_native] nproc=$(nproc) nproc_all=$(nproc --all)"
grep Cpus_allowed_list /proc/self/status || true
taskset -pc $$ || true
echo "[run_train_b99_6_resume_b99_5_iter25_native] SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-unset}"
echo "[run_train_b99_6_resume_b99_5_iter25_native] config=$CONFIG"
echo "[run_train_b99_6_resume_b99_5_iter25_native] resume=$B99_5_RESUME_CKPT"

python -u scripts/train_mpo.py \
  --config "$CONFIG" \
  --resume "$B99_5_RESUME_CKPT"
