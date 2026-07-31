#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T11_PYTHON:-${PYTHON:-python3}}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" \
  "${PROJECT_DIR}/scripts/stage4_2r3c3t11_persistent_step_response_identification.py" \
  --self-test
