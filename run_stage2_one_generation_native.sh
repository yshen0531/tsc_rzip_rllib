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
export STAGE2_WORKERS="${STAGE2_WORKERS:-192}"
export STAGE2_TSC_WORKSPACE_ROOT="${STAGE2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
export STAGE2_TSC_RUN_ROOT="${STAGE2_TSC_RUN_ROOT:-/tmp/tsc_workspace/episode_runs}"
export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage2_$(id -u)}"
export TMPDIR="$RAY_TMPDIR/tmp"
mkdir -p "$TMPDIR" stage2_runs

cleanup_stage2_tsc_tmp() {
  mkdir -p "$STAGE2_TSC_WORKSPACE_ROOT" "$STAGE2_TSC_RUN_ROOT"
  find "$STAGE2_TSC_WORKSPACE_ROOT" -mindepth 1 -maxdepth 1 -type d -name 'stage2_*' -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf "$STAGE2_TSC_RUN_ROOT"/* 2>/dev/null || true
}

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR/session_latest" >/dev/null 2>&1 || true
cleanup_stage2_tsc_tmp

CONFIG="${STAGE2_CONFIG:-configs/stage2_svd3_real_tsc_cem_100ms.json}"
if [[ -z "${STAGE2_RUN_DIR:-}" ]]; then
  STAGE2_RUN_DIR="stage2_runs/stage2_svd3_real_tsc_cem_100ms_$(date +%Y%m%d_%H%M%S)"
fi
if [[ -z "${SOURCE_STAGE1_1_RUN:-}" ]]; then
  if [[ -f "$STAGE2_RUN_DIR/stage2_manifest.json" ]]; then
    SOURCE_STAGE1_1_RUN="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_stage1_1_run"])' "$STAGE2_RUN_DIR/stage2_manifest.json")"
  elif [[ -f stage1_1_runs/latest_stage1_1_run.txt ]]; then
    SOURCE_STAGE1_1_RUN="$(cat stage1_1_runs/latest_stage1_1_run.txt)"
  else
    echo "Set SOURCE_STAGE1_1_RUN=/path/to/completed/Stage1.1/run" >&2
    exit 2
  fi
fi
mkdir -p "$STAGE2_RUN_DIR"
printf '%s\n' "$STAGE2_RUN_DIR" > stage2_runs/latest_stage2_run.txt

echo "[Stage2] RAY_TMPDIR=$RAY_TMPDIR"
echo "[Stage2] TSC_WORKSPACE_ROOT=${STAGE2_TSC_WORKSPACE_ROOT:-<source-config>}"
echo "[Stage2] TSC_RUN_ROOT=${STAGE2_TSC_RUN_ROOT:-<source-config>}"

set +e
python -u scripts/stage2_trajectory_optimization.py generation \
  --config "$CONFIG" \
  --source-run "$SOURCE_STAGE1_1_RUN" \
  --run-dir "$STAGE2_RUN_DIR" \
  --backend ray
STATUS=$?
set -e
ray stop --force >/dev/null 2>&1 || true
cleanup_stage2_tsc_tmp
exit "$STATUS"
