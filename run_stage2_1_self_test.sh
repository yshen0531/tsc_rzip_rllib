#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "${PROJECT_DIR}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
PYTHON_BIN="${PYTHON_BIN:-python}"
"${PYTHON_BIN}" -u scripts/stage2_1_trajectory_optimization.py self-test
"${PYTHON_BIN}" -m py_compile \
  scripts/stage2_1_trajectory_optimization.py \
  tsc_rzip_rllib/diagnostics/stage2_1_trajectory_optimization.py
python -m json.tool configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json >/dev/null
echo "Stage2.1 static/self-test passed."
