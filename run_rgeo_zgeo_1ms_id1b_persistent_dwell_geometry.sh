#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

: "${ID1B_SOURCE_REVISION:?set ID1B_SOURCE_REVISION to the 40-character implementation revision}"
: "${ID1B_OUTPUT:?set ID1B_OUTPUT to a new repository-local output directory}"

if [[ ! "$ID1B_SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid ID1B_SOURCE_REVISION" >&2
  exit 2
fi
if [[ "$ID1B_OUTPUT" != "$ROOT"/* ]] || [[ -e "$ID1B_OUTPUT" ]]; then
  echo "ID1B_OUTPUT must be a new path inside the repository" >&2
  exit 2
fi

set +e
python scripts/rgeo_zgeo_1ms_id1b_persistent_dwell_geometry.py run \
  --source-revision "$ID1B_SOURCE_REVISION" \
  --output "$ID1B_OUTPUT"
PRIMARY_RC=$?
set -e

if python - "$ID1B_OUTPUT/result.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if d.get("execution_passed") and d.get("raw_integrity_passed") else 1)
PY
then
  set +e
  python scripts/rgeo_zgeo_1ms_id1b_persistent_dwell_geometry_independent.py \
    --source-revision "$ID1B_SOURCE_REVISION" \
    --run-dir "$ID1B_OUTPUT"
  AUDIT_RC=$?
  set -e
  if [[ "$AUDIT_RC" -ne 0 ]]; then
    exit 2
  fi
fi

exit "$PRIMARY_RC"
