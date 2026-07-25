#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_0_shell_common.sh"
stage40_project_init
stage40_find_python
"${PYTHON_BIN}" -m compileall -q "${PROJECT_DIR}/tsc_rzip_rllib" "${PROJECT_DIR}/scripts" "${PROJECT_DIR}/tests"
"${PYTHON_BIN}" -m unittest discover -s "${PROJECT_DIR}/tests" -p 'test_*.py'
"${PYTHON_BIN}" -u "${PROJECT_DIR}/scripts/stage4_0_robustness_recovery.py" --synthetic-test
