#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

: "${ID2Z6_SOURCE_REVISION:?set implementation revision}"
: "${ID2Z6_OUTPUT:?set new repository-local output directory}"
case "$ID2Z6_OUTPUT" in
  "$ROOT"/*) ;;
  *) echo "output must be inside repository" >&2; exit 2 ;;
esac
test ! -e "$ID2Z6_OUTPUT"

python scripts/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher.py \
  --source-revision "$ID2Z6_SOURCE_REVISION" --offline-only \
  > "${ID2Z6_OUTPUT}.offline.json"
set +e
python scripts/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher.py \
  --source-revision "$ID2Z6_SOURCE_REVISION" --output "$ID2Z6_OUTPUT"
primary_rc=$?
if test -f "$ID2Z6_OUTPUT/result.json"; then
  python scripts/rgeo_zgeo_1ms_id2z6_early_root_branch_teacher_independent.py \
    --source-revision "$ID2Z6_SOURCE_REVISION" --run-dir "$ID2Z6_OUTPUT" \
    --output "$ID2Z6_OUTPUT/independent_raw_audit.json"
  audit_rc=$?
else
  audit_rc=2
fi
set -e
if (( audit_rc != 0 )); then exit "$audit_rc"; fi
exit "$primary_rc"
