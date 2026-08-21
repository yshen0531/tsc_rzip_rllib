#!/usr/bin/env bash
set -euo pipefail
: "${ID2Z36_SOURCE_REVISION:?ID2Z36_SOURCE_REVISION is required}"
: "${ID2Z36_OUTPUT:?ID2Z36_OUTPUT is required}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
test ! -e "$ID2Z36_OUTPUT"
python scripts/rgeo_zgeo_1ms_id2z36_engineering_floor_event_set.py \
  --source-revision "$ID2Z36_SOURCE_REVISION" \
  --output "$ID2Z36_OUTPUT"
python scripts/rgeo_zgeo_1ms_id2z36_engineering_floor_event_set_independent.py \
  --primary "$ID2Z36_OUTPUT" \
  --source-revision "$ID2Z36_SOURCE_REVISION" \
  --output "${ID2Z36_OUTPUT%.json}.independent.json"
