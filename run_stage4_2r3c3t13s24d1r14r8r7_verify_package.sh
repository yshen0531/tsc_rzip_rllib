#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
test -x "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python"
sha256sum -c SHA256SUMS
bash -n run_stage4_2r3c3t13s24d1r14r8r7_common.sh run_stage4_2r3c3t13s24d1r14r8r7_native.sh run_stage4_2r3c3t13s24d1r14r8r7_nohup.sh run_stage4_2r3c3t13s24d1r14r8r7_self_test.sh run_stage4_2r3c3t13s24d1r14r8r7_verify_package.sh scripts/stage4_2r3c3t13s24d1r14r8r7_shell_common.sh
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m py_compile scripts/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign.py docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r7_independent_forensics.py tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel.py tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_campaign.py
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m unittest tests.test_stage4_2r3c3t13s24d1r14r8r7_fresh_multipulse_static_observer_interaction_sentinel
