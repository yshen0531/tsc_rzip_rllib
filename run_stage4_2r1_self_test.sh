#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R1_PYTHON:-${PYTHON:-python3}}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
exec "${PYTHON_BIN}" "${PROJECT_DIR}/scripts/stage4_2r1_true_tsc_plant_restart_action_replay.py" --self-test
