#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R15_PYTHON:-${PYTHON:-python3}}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/stage4_1r15_bounded_early_braking_local_response_identification.py" --self-test
