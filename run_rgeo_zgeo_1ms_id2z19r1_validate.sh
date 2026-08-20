#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"

test -d "$PROJECT"
test -f "$VENV/bin/activate"
cd "$PROJECT"
test "$PWD" = "$PROJECT"
source "$VENV/bin/activate"

bash -n run_rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.sh
python -m py_compile \
  scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.py \
  scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model_audit.py \
  tests/test_rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.py
python -m unittest \
  tests.test_rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model -v
python -m unittest discover -s tests -p 'test_rgeo_zgeo_1ms*.py'
python scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.py \
  --preflight
