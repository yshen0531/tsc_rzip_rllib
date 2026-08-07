#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
test -x "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python"
sha256sum -c SHA256SUMS
bash -n \
  run_stage4_2r3c3t13s24d1r14r8r6_common.sh \
  run_stage4_2r3c3t13s24d1r14r8r6_native.sh \
  run_stage4_2r3c3t13s24d1r14r8r6_nohup.sh \
  run_stage4_2r3c3t13s24d1r14r8r6_self_test.sh \
  run_stage4_2r3c3t13s24d1r14r8r6_verify_package.sh \
  scripts/stage4_2r3c3t13s24d1r14r8r6_shell_common.sh
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m py_compile \
  scripts/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.py \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r6_independent_forensics.py \
  tsc_rzip_rllib/control/causal_one_step_innovation_observer.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer_audit.py
"/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python" -m unittest \
  tests.test_stage4_2r3c3t13s24d1r14r8r6_causal_one_step_innovation_observer
