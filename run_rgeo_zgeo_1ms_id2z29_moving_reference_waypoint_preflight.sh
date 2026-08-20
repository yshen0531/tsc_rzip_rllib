#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 2
REV="${ID2Z29_SOURCE_REVISION:?ID2Z29_SOURCE_REVISION is required}"
OUT="${ID2Z29_OUTPUT:?ID2Z29_OUTPUT is required}"
test ! -e "$OUT" || exit 2
mkdir -p "$OUT" || exit 2
python scripts/rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight.py \
  --source-revision "$REV" --output "$OUT/result.json"
primary_rc=$?
if [[ "$primary_rc" -ne 0 && "$primary_rc" -ne 2 ]]; then exit 2; fi
python scripts/rgeo_zgeo_1ms_id2z29_moving_reference_waypoint_preflight_independent.py \
  --primary "$OUT/result.json" --source-revision "$REV" \
  --output "$OUT/independent_audit.json" || exit 2
printf '%s\n' "$primary_rc" > "$OUT/primary_exit_code.txt"
exit 0
