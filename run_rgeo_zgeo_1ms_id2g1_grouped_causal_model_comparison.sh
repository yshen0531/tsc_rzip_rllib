#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"

test "${PWD}" = "${PROJECT}"
test -f "${VENV}/bin/activate"
test -n "${ID2G1_SOURCE_REVISION:-}"
test -n "${ID2G1_OUTPUT:-}"
case "${ID2G1_OUTPUT}" in
  /*|*..*) exit 2 ;;
esac
test ! -e "${ID2G1_OUTPUT}"

source "${VENV}/bin/activate"

python scripts/rgeo_zgeo_1ms_id2g1_grouped_causal_model.py preflight \
  --stage-config configs/rgeo_zgeo_1ms_id2g1_grouped_causal_model_comparison.json \
  --source-revision "${ID2G1_SOURCE_REVISION}" \
  --output ".codex_tmp/id2g1_preflight_${ID2G1_SOURCE_REVISION}.json"

python scripts/rgeo_zgeo_1ms_id2g1_grouped_causal_model.py run \
  --stage-config configs/rgeo_zgeo_1ms_id2g1_grouped_causal_model_comparison.json \
  --source-revision "${ID2G1_SOURCE_REVISION}" \
  --output "${ID2G1_OUTPUT}"

python scripts/rgeo_zgeo_1ms_id2g1_grouped_causal_model_independent.py \
  --stage-config configs/rgeo_zgeo_1ms_id2g1_grouped_causal_model_comparison.json \
  --primary "${ID2G1_OUTPUT}/result.json" \
  --source-revision "${ID2G1_SOURCE_REVISION}" \
  --output "${ID2G1_OUTPUT}/independent_audit.json"
