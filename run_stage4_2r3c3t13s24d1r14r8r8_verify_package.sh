#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
PYTHON="/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python"
test -x "${PYTHON}"
sha256sum -c SHA256SUMS
bash -n run_stage4_2r3c3t13s24d1r14r8r8_common.sh run_stage4_2r3c3t13s24d1r14r8r8_native.sh run_stage4_2r3c3t13s24d1r14r8r8_nohup.sh run_stage4_2r3c3t13s24d1r14r8r8_self_test.sh run_stage4_2r3c3t13s24d1r14r8r8_verify_package.sh scripts/stage4_2r3c3t13s24d1r14r8r8_shell_common.sh
"${PYTHON}" -m py_compile scripts/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_campaign.py docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r8_independent_forensics.py tsc_rzip_rllib/control/causal_discrete_pulse_mpc.py tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core.py tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_campaign.py
"${PYTHON}" -m unittest tests.test_stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core
