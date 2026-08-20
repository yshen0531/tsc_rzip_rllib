#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
OUTPUT="${ID2Z19R1_OUTPUT:?ID2Z19R1_OUTPUT is required}"
REVISION="${ID2Z19R1_SOURCE_REVISION:?ID2Z19R1_SOURCE_REVISION is required}"

test -d "$PROJECT"
test -f "$VENV/bin/activate"
cd "$PROJECT"
test "$PWD" = "$PROJECT"
test ! -e "$OUTPUT"

source "$VENV/bin/activate"
set +e
python scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.py \
  --source-revision "$REVISION" --output "$OUTPUT"
PRIMARY_STATUS=$?
set -e

AUDIT_STATUS=0
if test -f "$OUTPUT/result.json" && test -f "$OUTPUT/oof_predictions.json"; then
  set +e
  python scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model_audit.py \
    --output "$OUTPUT"
  AUDIT_STATUS=$?
  set -e
fi

if test "$PRIMARY_STATUS" -ne 0 || test "$AUDIT_STATUS" -ne 0; then
  exit 2
fi
