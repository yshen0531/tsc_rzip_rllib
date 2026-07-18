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
export STAGE1_WORKERS="${STAGE1_WORKERS:-9}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage11_$(id -u)}"
mkdir -p "$RAY_TMPDIR" "$RAY_TMPDIR/tmp" stage1_1_runs
export TMPDIR="$RAY_TMPDIR/tmp"

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true

CONFIG="${STAGE1_1_CONFIG:-configs/stage1_1_supplement_100ms.json}"
if [[ -z "${STAGE1_1_RUN_DIR:-}" ]]; then
  STAGE1_1_RUN_DIR="stage1_1_runs/stage1_1_svd234_strict_validation_100ms_$(date +%Y%m%d_%H%M%S)"
fi
if [[ -z "${SOURCE_STAGE1_RUN:-}" ]]; then
  if [[ -f "$STAGE1_1_RUN_DIR/stage1_1_manifest.json" ]]; then
    SOURCE_STAGE1_RUN="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_stage1_run"])' "$STAGE1_1_RUN_DIR/stage1_1_manifest.json")"
  elif [[ -f stage1_runs/latest_stage1_run.txt ]]; then
    SOURCE_STAGE1_RUN="$(cat stage1_runs/latest_stage1_run.txt)"
  else
    echo "Set SOURCE_STAGE1_RUN=/path/to/completed/Stage1/run" >&2
    exit 2
  fi
fi
mkdir -p "$STAGE1_1_RUN_DIR"
printf '%s\n' "$STAGE1_1_RUN_DIR" > stage1_1_runs/latest_stage1_1_run.txt

cat <<EOF
[Stage1.1] user=$(whoami) host=$(hostname) pwd=$(pwd)
[Stage1.1] source_stage1_run=$SOURCE_STAGE1_RUN
[Stage1.1] run_dir=$STAGE1_1_RUN_DIR
[Stage1.1] config=$CONFIG
[Stage1.1] validation_workers=$STAGE1_WORKERS
[Stage1.1] RAY_TMPDIR=$RAY_TMPDIR
[Stage1.1] Retry plan is 12-worker Ray -> 4-worker Ray -> serial for only failed/missing experiments.
[Stage1.1] Immediate TERM/KILL is not intercepted. Completed per-experiment files remain resumable.
EOF

exec python -u scripts/stage1_1_supplement.py all \
  --config "$CONFIG" \
  --source-run "$SOURCE_STAGE1_RUN" \
  --run-dir "$STAGE1_1_RUN_DIR" \
  --backend ray
