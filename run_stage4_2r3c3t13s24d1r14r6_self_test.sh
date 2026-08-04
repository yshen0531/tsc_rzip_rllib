#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R6_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" scripts/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel.py \
  --config "${PROJECT_DIR}/configs/stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel_370ms.json" --self-test
