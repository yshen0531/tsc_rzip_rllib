#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2V0_SOURCE_REVISION:?ID2V0_SOURCE_REVISION is required}"
OUTPUT="${ID2V0_OUTPUT:-$ROOT/rgeo_zgeo_1ms_id2v0_${ID2V0_SOURCE_REVISION:0:8}}"

test ! -e "$OUTPUT"
python scripts/rgeo_zgeo_1ms_id2v0_control_utility_support_audit.py \
  --source-revision "$ID2V0_SOURCE_REVISION" \
  --output "$OUTPUT"
python scripts/rgeo_zgeo_1ms_id2v0_control_utility_support_independent.py \
  --primary-result "$OUTPUT/result.json" \
  --output "$OUTPUT/independent_audit.json"

printf 'ID2V0_OUTPUT=%s\n' "$OUTPUT"

