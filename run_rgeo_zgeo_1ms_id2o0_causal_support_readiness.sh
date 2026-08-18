#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2O0_SOURCE_REVISION:?set ID2O0_SOURCE_REVISION to the deployed implementation commit}"
: "${ID2O0_OUTPUT:?set ID2O0_OUTPUT to a new repository-local output directory}"

case "$ID2O0_OUTPUT" in
  "$ROOT"/*) ;;
  *) echo "ID2O0_OUTPUT must be inside $ROOT" >&2; exit 2 ;;
esac
test ! -e "$ID2O0_OUTPUT"
mkdir -p "$ID2O0_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2o0_causal_support_readiness_audit.py \
  --source-revision "$ID2O0_SOURCE_REVISION" \
  --output "$ID2O0_OUTPUT/result.json"
python scripts/rgeo_zgeo_1ms_id2o0_causal_support_readiness_independent.py \
  --source-revision "$ID2O0_SOURCE_REVISION" \
  --primary "$ID2O0_OUTPUT/result.json" \
  --output "$ID2O0_OUTPUT/independent_audit.json"
