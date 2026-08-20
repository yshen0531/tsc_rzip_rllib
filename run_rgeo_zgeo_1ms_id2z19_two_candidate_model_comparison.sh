#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
OUTPUT="${ID2Z19_OUTPUT:?ID2Z19_OUTPUT is required}"
REVISION="${ID2Z19_SOURCE_REVISION:?ID2Z19_SOURCE_REVISION is required}"

test -d "$PROJECT"
test -f "$VENV/bin/activate"
cd "$PROJECT"
test "$PWD" = "$PROJECT"
test ! -e "$OUTPUT"

source "$VENV/bin/activate"
python scripts/rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison.py \
  --source-revision "$REVISION" --output "$OUTPUT"
python scripts/rgeo_zgeo_1ms_id2z19_two_candidate_model_comparison_audit.py \
  --output "$OUTPUT"
