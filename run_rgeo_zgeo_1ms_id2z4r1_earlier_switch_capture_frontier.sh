#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2Z4R1_SOURCE_REVISION:?set implementation revision}"
: "${ID2Z4R1_OUTPUT:?set new repository-local output directory}"
case "$ID2Z4R1_OUTPUT" in
  "$ROOT"/*) ;;
  *) echo "output must be inside repository" >&2; exit 2 ;;
esac
test ! -e "$ID2Z4R1_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier.py \
  --source-revision "$ID2Z4R1_SOURCE_REVISION" --offline-only \
  > "${ID2Z4R1_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier.py \
  --source-revision "$ID2Z4R1_SOURCE_REVISION" --output "$ID2Z4R1_OUTPUT"
primary_rc=$?
if test -f "$ID2Z4R1_OUTPUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z4r1_earlier_switch_capture_frontier_independent.py \
    --source-revision "$ID2Z4R1_SOURCE_REVISION" --run-dir "$ID2Z4R1_OUTPUT" \
    --output "$ID2Z4R1_OUTPUT/independent_raw_audit.json"
  audit_rc=$?
else
  audit_rc=2
fi
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
