#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r10_shell_common.sh"
stage4_2r3c3t13s24d1r10_validate_common
stage4_2r3c3t13s24d1r10_export_runtime
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R10_PYTHON}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r10_exact_row_completion_safety_sentinel \
  tests.test_stage4_2r3c3t13s24_sequential_transition_identification \
  tests.test_stage4_2r3c3t13s24d1r9_central_row_replacement_preflight
