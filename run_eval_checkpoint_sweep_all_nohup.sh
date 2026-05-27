#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# All-in-one B83 checkpoint sweep + stochastic eval.
# Runs all checkpoints x all stages x deterministic/stochastic in one sweep.
#
# Usage:
#   ./run_eval_checkpoint_sweep_all_nohup.sh \
#       ray_checkpoints/train_b83_192worker_5m_20260520_142028 \
#       64 \
#       2 \
#       1.0
#
# Args:
#   $1 checkpoint root, default: latest train_b83 checkpoint dir
#   $2 num parallel eval jobs, default: 64
#   $3 Ray CPUs per eval job, default: 2
#   $4 startup stagger seconds, default: 1.0
#
# Notes:
#   Each eval job launches one local Ray instance + one TSC env.  Starting too many
#   independent Ray instances simultaneously can hit fork/nproc/thread limits even
#   when CPU is available.  This wrapper runs the full sweep in one round but ramps
#   up launches gradually and retries transient Ray startup failures.

CKPT_ROOT="${1:-}"
NUM_WORKERS="${2:-64}"
RAY_CPUS_PER_JOB="${3:-2}"
STARTUP_STAGGER_SEC="${4:-1.0}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_SLEEP_SEC="${RETRY_SLEEP_SEC:-25}"
RETRY_BACKOFF="${RETRY_BACKOFF:-1.6}"

if [[ -z "$CKPT_ROOT" ]]; then
  CKPT_ROOT="$(ls -td ray_checkpoints/train_b83_* 2>/dev/null | head -1 || true)"
fi

if [[ -z "$CKPT_ROOT" || ! -d "$CKPT_ROOT" ]]; then
  echo "ERROR: checkpoint root not found: ${CKPT_ROOT:-<empty>}" >&2
  echo "Usage: ./run_eval_checkpoint_sweep_all_nohup.sh ray_checkpoints/<run_name> [num_workers] [ray_cpus_per_job] [startup_stagger_sec]" >&2
  exit 1
fi

LOG_DIR="logs/eval_sweep_nohup"
PID_DIR="logs/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
RUN_TAG="$(basename "$CKPT_ROOT")"
LOG_FILE="${LOG_DIR}/checkpoint_sweep_all_${RUN_TAG}_${STAMP}.log"
PID_FILE="${PID_DIR}/checkpoint_sweep_all_${RUN_TAG}_${STAMP}.pid"

export PYTHONPATH="$PWD:${PYTHONPATH:-}"

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

unset RAY_ADDRESS || true
unset RAY_NAMESPACE || true

TOTAL_CPUS=$(( NUM_WORKERS * RAY_CPUS_PER_JOB ))
RAY_TMP_ROOT="/tmp/rs$(id -u)"
mkdir -p "$RAY_TMP_ROOT"

# Keep the old too-long tmp root out of the way.
rm -rf "/tmp/ry_eval_sweep_${USER:-user}" 2>/dev/null || true

echo "Starting ALL checkpoint sweep + stochastic eval with nohup..."
echo "Checkpoint root     : $CKPT_ROOT"
echo "Num workers         : $NUM_WORKERS"
echo "Ray CPUs/job        : $RAY_CPUS_PER_JOB"
echo "Approx CPUs         : $TOTAL_CPUS"
echo "Startup stagger sec : $STARTUP_STAGGER_SEC"
echo "Max retries         : $MAX_RETRIES"
echo "Retry sleep/backoff : $RETRY_SLEEP_SEC / $RETRY_BACKOFF"
echo "Ray tmp root        : $RAY_TMP_ROOT"
echo "Stages              : stage0,stage1,stage2,final"
echo "Modes               : deterministic,stochastic"
echo "Det episodes        : 1"
echo "Stoch episodes      : 3"
echo "Log                 : $LOG_FILE"
echo "PID file            : $PID_FILE"
echo

nohup setsid bash run_eval_checkpoint_sweep.sh \
  --checkpoint-root "$CKPT_ROOT" \
  --config configs/rllib_sac.json \
  --checkpoint-stride 25 \
  --stages stage0,stage1,stage2,final \
  --modes deterministic,stochastic \
  --episodes-deterministic 1 \
  --episodes-stochastic 3 \
  --num-workers "$NUM_WORKERS" \
  --ray-cpus-per-job "$RAY_CPUS_PER_JOB" \
  --ray-tmp-root "$RAY_TMP_ROOT" \
  --startup-stagger-sec "$STARTUP_STAGGER_SEC" \
  --max-retries "$MAX_RETRIES" \
  --retry-sleep-sec "$RETRY_SLEEP_SEC" \
  --retry-backoff "$RETRY_BACKOFF" \
  > "$LOG_FILE" 2>&1 < /dev/null &

PID=$!
echo "$PID" > "$PID_FILE"
ln -sfn "$PID_FILE" "${PID_DIR}/latest_eval_sweep.pid"
ln -sfn "$LOG_FILE" "${LOG_DIR}/latest.log"

echo "Started."
echo "PID: $PID"
echo "Log: $LOG_FILE"
echo
echo "Monitor:"
echo "  tail -f ${LOG_DIR}/latest.log"
echo
echo "Stop:"
echo "  bash stop_eval_checkpoint_sweep.sh"
echo
echo "After finish:"
echo "  latest=\$(ls -td eval_sweeps/*sweep_* | head -1)"
echo "  column -s, -t \"\$latest/sweep_results.csv\" | less -S"
