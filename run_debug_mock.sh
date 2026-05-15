#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/ry_${USER}}"
export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"

ray stop --force >/dev/null 2>&1 || true

rm -rf "$RAY_TMPDIR"
mkdir -p "$RAY_TMPDIR"
mkdir -p "$TMPDIR"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

python scripts/train_rllib_sac.py \
  --config configs/rllib_sac.json \
  --override configs/debug_mock.json