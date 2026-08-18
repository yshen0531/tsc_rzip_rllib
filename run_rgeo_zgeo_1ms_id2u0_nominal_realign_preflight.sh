#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2U0_SOURCE_REVISION:?set ID2U0_SOURCE_REVISION to the deployed implementation commit}"
OUTPUT_DIR="${ID2U0_OUTPUT_DIR:-$ROOT/rgeo_zgeo_1ms_id2u0_${ID2U0_SOURCE_REVISION:0:8}}"
test ! -e "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

python scripts/rgeo_zgeo_1ms_id2u0_nominal_realign_preflight.py \
  --source-revision "$ID2U0_SOURCE_REVISION" \
  --output "$OUTPUT_DIR/result.json"
python scripts/rgeo_zgeo_1ms_id2u0_nominal_realign_preflight_independent.py \
  --primary-result "$OUTPUT_DIR/result.json" \
  --output "$OUTPUT_DIR/independent_audit.json"

printf '%s\n' "$OUTPUT_DIR"
