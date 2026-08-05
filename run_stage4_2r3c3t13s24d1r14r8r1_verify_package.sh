#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R8R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo 'ERROR: server virtualenv Python not executable' >&2; exit 1; }
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m py_compile \
  scripts/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.py \
  docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r1_independent_forensics.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.py
"${PYTHON_BIN}" -m json.tool configs/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.json >/dev/null
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
STAGE4_2R3C3T13S24D1R14R8R1_COMMAND=self-test bash run_stage4_2r3c3t13s24d1r14r8r1_native.sh
"${PYTHON_BIN}" -m unittest -v tests.test_stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator
printf '[R8R1 verify] hashes, compile, JSON, shell syntax, self-test and focused tests passed.\n'
