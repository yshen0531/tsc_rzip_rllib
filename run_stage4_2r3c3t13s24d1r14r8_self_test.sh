#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R8_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_DIR}"
exec "${PYTHON_BIN}" scripts/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification.py \
  --config configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json \
  --source-d1r11-run . --source-r2-run . --source-r4-run . --source-r6-run . \
  --source-s21-run . --source-s23r1-output . --source-s24-run . --source-d1r9-v1 . --source-d1r9-v2 . \
  --source-d1r10-run . --source-d1r10-audit . --source-stage42r3b-run . --source-stage42r3c3-run . \
  --source-stage42r3c3-bank-dir . --source-stage42r3c3t1-run . --source-stage42r3c3t1-audit-dir . \
  --source-stage42r3c3t3-controller-bank . --q1-run . --q2-run . --q1-audit . --q2-audit . \
  --r3b-server-audit . --r3b-snapshot-checks . --run-dir . --command offline --self-test
