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

export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "$PROJECT_DIR/.." && pwd)}"
export STAGE1_WORKERS="${STAGE1_WORKERS:-192}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/rm$(id -u)}"
mkdir -p "$RAY_TMPDIR" "$RAY_TMPDIR/tmp"
export TMPDIR="$RAY_TMPDIR/tmp"

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

CONFIG="${STAGE1_CONFIG:-configs/stage1_controllability_100ms.json}"
if [[ -z "${STAGE1_RUN_DIR:-}" ]]; then
  STAGE1_RUN_DIR="stage1_runs/stage1_controllability_100ms_$(date +%Y%m%d_%H%M%S)"
fi
mkdir -p "$STAGE1_RUN_DIR"
printf '%s\n' "$STAGE1_RUN_DIR" > stage1_runs/latest_stage1_run.txt

cat <<EOF
[Stage1] user=$(whoami) host=$(hostname) pwd=$(pwd)
[Stage1] config=$CONFIG
[Stage1] run_dir=$STAGE1_RUN_DIR
[Stage1] workers=$STAGE1_WORKERS
[Stage1] RAY_TMPDIR=$RAY_TMPDIR
[Stage1] Immediate TERM/KILL is not intercepted. Completed per-experiment files remain resumable.
EOF

exec python -u scripts/stage1_controllability.py all \
  --config "$CONFIG" \
  --run-dir "$STAGE1_RUN_DIR" \
  --backend ray
