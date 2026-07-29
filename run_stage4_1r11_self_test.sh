#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R11_PYTHON:-${PYTHON:-python3}}"
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PROJECT_DIR}"
"${PYTHON_BIN}" -m tsc_rzip_rllib.diagnostics.stage4_1r11_frozen_terminal_long_horizon_hold --self-test
