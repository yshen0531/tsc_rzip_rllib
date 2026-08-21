#!/usr/bin/env bash
set -uo pipefail

: "${ID2Z34_SOURCE_REVISION:?ID2Z34_SOURCE_REVISION is required}"
: "${ID2Z34_OUTPUT:?ID2Z34_OUTPUT is required}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
test "$PWD" = "$ROOT"
mkdir -p "$ID2Z34_OUTPUT"
test ! -e "$ID2Z34_OUTPUT/result.json"
test ! -e "$ID2Z34_OUTPUT/independent_audit.json"

set +e
python scripts/rgeo_zgeo_1ms_id2z34_event_set_model.py \
  --source-revision "$ID2Z34_SOURCE_REVISION" \
  --output "$ID2Z34_OUTPUT/result.json"
primary_rc=$?
python scripts/rgeo_zgeo_1ms_id2z34_event_set_model_independent.py \
  --primary "$ID2Z34_OUTPUT/result.json" \
  --source-revision "$ID2Z34_SOURCE_REVISION" \
  --output "$ID2Z34_OUTPUT/independent_audit.json"
audit_rc=$?
set -e

if [[ $audit_rc -ne 0 ]]; then
  exit "$audit_rc"
fi
exit "$primary_rc"
