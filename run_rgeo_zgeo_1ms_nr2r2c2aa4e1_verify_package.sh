#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "${PROJECT_DIR}"

PYTHON="${C2AA4E1_PACKAGE_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
EXPECTED_MANIFEST_SHA256="${C2AA4E1_EXPECTED_MANIFEST_SHA256:?C2AA4E1_EXPECTED_MANIFEST_SHA256 is required}"
EXPECTED_CHECKSUM_SHA256="${C2AA4E1_EXPECTED_CHECKSUM_SHA256:?C2AA4E1_EXPECTED_CHECKSUM_SHA256 is required}"
PACKAGE_TOOL_REVISION="${C2AA4E1_PACKAGE_TOOL_REVISION:?C2AA4E1_PACKAGE_TOOL_REVISION is required}"

test -x "${PYTHON}"
bash -n \
  run_rgeo_zgeo_1ms_nr2r2c2aa4e1.sh \
  run_rgeo_zgeo_1ms_nr2r2c2aa4e1_verify_package.sh
export PYTHONDONTWRITEBYTECODE=1
exec "${PYTHON}" scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_verify_package.py \
  --repo-root "${PROJECT_DIR}" \
  --expected-manifest-sha256 "${EXPECTED_MANIFEST_SHA256}" \
  --expected-checksum-sha256 "${EXPECTED_CHECKSUM_SHA256}" \
  --expected-package-tool-revision "${PACKAGE_TOOL_REVISION}" \
  --require-runtime-paths
