#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${PROJECT_DIR}/scripts/stage4_2r3c3t13s24d1r2_shell_common.sh"
stage4_2r3c3t13s24d1r2_validate_common
stage4_2r3c3t13s24d1r2_export_runtime
cd "${PROJECT_DIR}"
exec "${STAGE4_2R3C3T13S24D1R2_PYTHON}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r2_real_tsc_safety_sentinel \
  tests.test_stage4_2r3c3t13s24_sequential_transition_identification \
  tests.test_stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search
