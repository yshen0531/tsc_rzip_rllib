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

CONFIG="configs/mpo_b99_10_resume_b99_9_train_first_light_transaction_runtime_only_192worker.json"

# One B99.9 run supplies mature critics from its latest complete periodic
# checkpoint and the protected tenth accepted actor from accepted_latest.
if [[ -z "${B99_9_RUN_DIR:-}" ]]; then
  B99_9_RUN_DIR="$(ls -dt mpo_checkpoints/train_b99_9_resume_b99_8_transactional_line_search_ip_relaxed_runtime_only_mpo_192worker_* 2>/dev/null | head -1 || true)"
fi
if [[ -z "$B99_9_RUN_DIR" || ! -d "$B99_9_RUN_DIR" ]]; then
  echo "[B99.10] ERROR: B99.9 run directory not found." >&2
  echo "Set B99_9_RUN_DIR=/path/to/train_b99_9... checkpoint directory." >&2
  exit 2
fi

B99_9_ACCEPTED_CKPT="${B99_9_ACCEPTED_CKPT:-$B99_9_RUN_DIR/accepted_latest}"
if [[ -z "${B99_9_BASE_CKPT:-}" ]]; then
  # Intentionally prefer a complete periodic checkpoint over final: B99.9 was
  # hard-stopped and may not have a valid final directory.
  B99_9_BASE_CKPT="$(find "$B99_9_RUN_DIR" -maxdepth 1 -type d -name 'iter_*' -print | sort | tail -1 || true)"
fi

if [[ ! -f "$B99_9_BASE_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.10] ERROR: complete B99.9 periodic checkpoint not found: $B99_9_BASE_CKPT" >&2
  echo "Set B99_9_BASE_CKPT=/path/to/iter_000170 (or another complete iter_*)." >&2
  exit 2
fi
if [[ ! -f "$B99_9_ACCEPTED_CKPT/mpo_checkpoint.pt" ]]; then
  echo "[B99.10] ERROR: B99.9 accepted_latest actor checkpoint not found: $B99_9_ACCEPTED_CKPT" >&2
  echo "Set B99_9_ACCEPTED_CKPT=/path/to/accepted_latest." >&2
  exit 2
fi

BASE_REAL="$(readlink -f "$B99_9_BASE_CKPT")"
ACTOR_REAL="$(readlink -f "$B99_9_ACCEPTED_CKPT")"
RUN_REAL="$(readlink -f "$B99_9_RUN_DIR")"
case "$BASE_REAL" in "$RUN_REAL"/*) ;; *) echo "[B99.10] ERROR: base checkpoint is not inside selected B99.9 run." >&2; exit 2;; esac
case "$ACTOR_REAL" in "$RUN_REAL"/*) ;; *) echo "[B99.10] ERROR: actor checkpoint is not inside selected B99.9 run." >&2; exit 2;; esac

echo "[B99.10] user=$(whoami) host=$(hostname) pwd=$(pwd)"
echo "[B99.10] ulimit -n=$(ulimit -n) ulimit -u=$(ulimit -u)"
echo "[B99.10] RAY_TMPDIR=$RAY_TMPDIR"
echo "[B99.10] nproc=$(nproc) nproc_all=$(nproc --all)"
grep Cpus_allowed_list /proc/self/status || true
taskset -pc $$ || true
echo "[B99.10] config=$CONFIG"
echo "[B99.10] base critics checkpoint=$B99_9_BASE_CKPT"
echo "[B99.10] protected accepted actor=$B99_9_ACCEPTED_CKPT"
echo "[B99.10] Signals are NOT intercepted. TERM/KILL stops immediately; no final save is promised."

exec python -u scripts/train_mpo.py \
  --config "$CONFIG" \
  --resume "$B99_9_BASE_CKPT" \
  --policy-resume "$B99_9_ACCEPTED_CKPT"
