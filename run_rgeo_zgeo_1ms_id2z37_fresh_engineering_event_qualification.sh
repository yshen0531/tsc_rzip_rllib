#!/usr/bin/env bash
set -uo pipefail

: "${ID2Z37_SOURCE_REVISION:?ID2Z37_SOURCE_REVISION is required}"
: "${ID2Z37_OUTPUT:?ID2Z37_OUTPUT is required}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
test "$PWD" = "$ROOT"
test ! -e "$ID2Z37_OUTPUT"

set +e
python scripts/rgeo_zgeo_1ms_id2z37_fresh_engineering_event_qualification.py \
  --source-revision "$ID2Z37_SOURCE_REVISION" \
  --output "$ID2Z37_OUTPUT"
primary_rc=$?
python scripts/rgeo_zgeo_1ms_id2z37_fresh_engineering_event_qualification_independent.py \
  --run-dir "$ID2Z37_OUTPUT" \
  --source-revision "$ID2Z37_SOURCE_REVISION" \
  --output "$ID2Z37_OUTPUT/independent_raw_audit.json"
audit_rc=$?
set -e

if [[ $audit_rc -ne 0 ]]; then
  exit "$audit_rc"
fi
exit "$primary_rc"
