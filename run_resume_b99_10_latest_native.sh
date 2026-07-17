#!/usr/bin/env bash
set -euo pipefail

ulimit -u 262144 || true
ulimit -n 1048576 || true
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1
export TORCH_NUM_THREADS=1 TORCH_NUM_INTEROP_THREADS=1 RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/rm$(id -u)}"
mkdir -p "$RAY_TMPDIR" "$RAY_TMPDIR/tmp"
export TMPDIR="$RAY_TMPDIR/tmp"
ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

CONFIG="configs/mpo_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_192worker.json"
if [[ -z "${B99_10_RUN_DIR:-}" ]]; then
  B99_10_RUN_DIR="$(ls -dt mpo_checkpoints/train_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_mpo_192worker_* 2>/dev/null | head -1 || true)"
fi
if [[ -z "$B99_10_RUN_DIR" || ! -d "$B99_10_RUN_DIR" ]]; then
  echo "[B99.10 resume] ERROR: B99.10 run directory not found." >&2
  echo "Set B99_10_RUN_DIR=/path/to/train_b99_10... checkpoint directory." >&2
  exit 2
fi
B99_10_ACCEPTED_CKPT="${B99_10_ACCEPTED_CKPT:-$B99_10_RUN_DIR/accepted_latest}"
if [[ -z "${B99_10_BASE_CKPT:-}" ]]; then
  B99_10_BASE_CKPT="$(find "$B99_10_RUN_DIR" -maxdepth 1 -type d -name 'iter_*' -print | sort | tail -1 || true)"
fi
if [[ ! -f "$B99_10_BASE_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.10 resume] ERROR: complete periodic checkpoint not found: $B99_10_BASE_CKPT" >&2
  exit 2
fi
if [[ ! -f "$B99_10_ACCEPTED_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.10 resume] ERROR: accepted_latest checkpoint not found: $B99_10_ACCEPTED_CKPT" >&2
  exit 2
fi
RUN_REAL="$(readlink -f "$B99_10_RUN_DIR")"
BASE_REAL="$(readlink -f "$B99_10_BASE_CKPT")"
ACTOR_REAL="$(readlink -f "$B99_10_ACCEPTED_CKPT")"
case "$BASE_REAL" in "$RUN_REAL"/*) ;; *) echo "[B99.10 resume] ERROR: base checkpoint is outside selected run." >&2; exit 2;; esac
case "$ACTOR_REAL" in "$RUN_REAL"/*) ;; *) echo "[B99.10 resume] ERROR: actor checkpoint is outside selected run." >&2; exit 2;; esac

echo "[B99.10 resume] base critics=$B99_10_BASE_CKPT"
echo "[B99.10 resume] accepted actor/state=$B99_10_ACCEPTED_CKPT"
echo "[B99.10 resume] Signals are NOT intercepted. TERM/KILL stops immediately."
exec python -u scripts/train_mpo.py --config "$CONFIG" --resume "$B99_10_BASE_CKPT" --policy-resume "$B99_10_ACCEPTED_CKPT"
