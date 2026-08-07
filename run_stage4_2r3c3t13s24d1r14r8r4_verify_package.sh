#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
test -x "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python"
sha256sum -c SHA256SUMS
bash -n \
  run_stage4_2r3c3t13s24d1r14r8r4_common.sh \
  run_stage4_2r3c3t13s24d1r14r8r4_native.sh \
  run_stage4_2r3c3t13s24d1r14r8r4_nohup.sh \
  run_stage4_2r3c3t13s24d1r14r8r4_self_test.sh \
  run_stage4_2r3c3t13s24d1r14r8r4_verify_package.sh \
  scripts/stage4_2r3c3t13s24d1r14r8r4_shell_common.sh
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m py_compile \
  scripts/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign.py \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r4_independent_forensics.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_campaign.py
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m unittest \
  tests.test_stage4_2r3c3t13s24d1r14r8r4_fresh_causal_observer_identification
