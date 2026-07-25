#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/scripts/stage4_1r2_shell_common.sh"
stage41r2_project_init
stage41r2_find_python
"${PYTHON_BIN}" -m compileall -q "${PROJECT_DIR}/scripts" "${PROJECT_DIR}/tsc_rzip_rllib" "${PROJECT_DIR}/tests"
"${PYTHON_BIN}" "${PROJECT_DIR}/scripts/stage4_1r2_error_state_robustness.py" --self-test
"${PYTHON_BIN}" -m unittest discover -s "${PROJECT_DIR}/tests" -p 'test_*.py' -v
