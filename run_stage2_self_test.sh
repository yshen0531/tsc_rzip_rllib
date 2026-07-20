#!/usr/bin/env bash
set -euo pipefail
export PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
python -u scripts/stage2_trajectory_optimization.py self-test
python -m py_compile scripts/stage2_trajectory_optimization.py \
  tsc_rzip_rllib/diagnostics/stage2_trajectory_optimization.py
