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

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

CONFIG="configs/mpo_b99_9_resume_b99_8_transactional_line_search_ip_relaxed_runtime_only_192worker.json"

# Select one B99.8 run, then take mature critics from its final/latest periodic
# checkpoint and the protected actor from the same run's best_error_score.
if [[ -z "${B99_8_RUN_DIR:-}" ]]; then
  B99_8_RUN_DIR="$(ls -dt mpo_checkpoints/train_b99_8_resume_b99_6_best_error_actor_guard_ip_relaxed_runtime_only_mpo_192worker_* 2>/dev/null | head -1 || true)"
fi

if [[ -z "$B99_8_RUN_DIR" || ! -d "$B99_8_RUN_DIR" ]]; then
  echo "[B99.9] ERROR: B99.8 checkpoint run directory not found." >&2
  echo "Set B99_8_RUN_DIR=/path/to/train_b99_8... checkpoint directory." >&2
  exit 2
fi

B99_8_BEST_ERROR_CKPT="${B99_8_BEST_ERROR_CKPT:-$B99_8_RUN_DIR/best_error_score}"
if [[ -z "${B99_8_BASE_CKPT:-}" ]]; then
  if [[ -f "$B99_8_RUN_DIR/final/mpo_checkpoint.pt" ]]; then
    B99_8_BASE_CKPT="$B99_8_RUN_DIR/final"
  else
    B99_8_BASE_CKPT="$(find "$B99_8_RUN_DIR" -maxdepth 1 -type d -name 'iter_*' -print | sort | tail -1 || true)"
  fi
fi

if [[ ! -f "$B99_8_BASE_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.9] ERROR: mature B99.8 base checkpoint not found: $B99_8_BASE_CKPT" >&2
  echo "Set B99_8_BASE_CKPT=/path/to/final_or_iter_checkpoint." >&2
  exit 2
fi
if [[ ! -f "$B99_8_BEST_ERROR_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.9] ERROR: B99.8 best_error_score checkpoint not found: $B99_8_BEST_ERROR_CKPT" >&2
  echo "Set B99_8_BEST_ERROR_CKPT=/path/to/best_error_score." >&2
  exit 2
fi

echo "[B99.9] user=$(whoami) host=$(hostname) pwd=$(pwd)"
echo "[B99.9] ulimit -n=$(ulimit -n) ulimit -u=$(ulimit -u)"
echo "[B99.9] RAY_TMPDIR=$RAY_TMPDIR"
echo "[B99.9] nproc=$(nproc) nproc_all=$(nproc --all)"
grep Cpus_allowed_list /proc/self/status || true
taskset -pc $$ || true
echo "[B99.9] config=$CONFIG"
echo "[B99.9] base critics checkpoint=$B99_8_BASE_CKPT"
echo "[B99.9] protected policy checkpoint=$B99_8_BEST_ERROR_CKPT"

python -u scripts/train_mpo.py \
  --config "$CONFIG" \
  --resume "$B99_8_BASE_CKPT" \
  --policy-resume "$B99_8_BEST_ERROR_CKPT"
