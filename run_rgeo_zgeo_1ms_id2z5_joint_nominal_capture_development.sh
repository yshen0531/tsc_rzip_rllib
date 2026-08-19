#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2Z5_SOURCE_REVISION:?set implementation revision}"
: "${ID2Z5_OUTPUT:?set new repository-local output directory}"
case "$ID2Z5_OUTPUT" in
  "$ROOT"/*) ;;
  *) echo "output must be inside repository" >&2; exit 2 ;;
esac
test ! -e "$ID2Z5_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development.py \
  --source-revision "$ID2Z5_SOURCE_REVISION" --offline-only \
  > "${ID2Z5_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development.py \
  --source-revision "$ID2Z5_SOURCE_REVISION" --output "$ID2Z5_OUTPUT"
primary_rc=$?
if test -f "$ID2Z5_OUTPUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z5_joint_nominal_capture_development_independent.py \
    --source-revision "$ID2Z5_SOURCE_REVISION" --run-dir "$ID2Z5_OUTPUT" \
    --output "$ID2Z5_OUTPUT/independent_raw_audit.json"
  audit_rc=$?
else
  audit_rc=2
fi
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
