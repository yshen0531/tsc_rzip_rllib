#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

CONFIG="${1:-configs/train_b83_192worker_5m.json}"

# Infer requested worker count from the merged RLlib config for the nproc fuse.
# This does not control Ray parallelism; it only sets a safe user-task soft limit.
NUM_TSC_WORKERS="${NUM_TSC_WORKERS:-$(python - "$CONFIG" <<'PY'
import json, sys
from pathlib import Path

def deep_update(a, b):
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_update(out[k], v)
        else:
            out[k] = v
    return out

base = json.load(open('configs/rllib_sac.json', encoding='utf-8'))
ov_path = Path(sys.argv[1])
ov = json.load(open(ov_path, encoding='utf-8')) if ov_path.exists() else {}
cfg = deep_update(base, ov)
print(int(cfg.get('parallel', {}).get('num_tsc_workers', 96)))
PY
)}"

# Raise soft limits when the hard limits allow it, but keep a finite
# safety fuse so a runaway worker/thread leak cannot consume all user tasks.
NPROC_LIMIT=$((5000 + NUM_TSC_WORKERS * 200))
if (( NPROC_LIMIT < 30000 )); then
  NPROC_LIMIT=30000
fi
if (( NPROC_LIMIT > 50000 )); then
  NPROC_LIMIT=50000
fi
ulimit -u "$NPROC_LIMIT" || true
ulimit -n 4096 || true

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

# Short Ray tmp path. Avoid AF_UNIX socket path length issues.
# Force training to use the training Ray tmpdir; do not inherit eval's
# /tmp/ry_eval_${USER} from the caller's shell.
export RAY_TMPDIR="/tmp/ry_${USER}"
export TMPDIR="${RAY_TMPDIR}/tmp"

ray stop --force >/dev/null 2>&1 || true
rm -rf "$RAY_TMPDIR"
mkdir -p "$RAY_TMPDIR" "$TMPDIR"

# Prevent every Ray worker / PyTorch / BLAS from spawning many threads.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export TORCH_NUM_INTEROP_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export BLIS_NUM_THREADS=1
export RAYON_NUM_THREADS=1
export RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO=0

echo "========== limits =========="
ulimit -u
ulimit -n
echo "threads before:"
ps -u "$USER" -L --no-headers | wc -l
echo "processes before:"
ps -u "$USER" --no-headers | wc -l
echo "============================"

python scripts/train_rllib_sac.py \
  --config configs/rllib_sac.json \
  --override "$CONFIG"
