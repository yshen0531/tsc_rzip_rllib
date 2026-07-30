#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C1_PYTHON:-${PYTHON:-python3}}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" \
  "${PROJECT_DIR}/scripts/stage4_2r3c1_authenticated_visible_manifold_phase_mpc.py" \
  --self-test
