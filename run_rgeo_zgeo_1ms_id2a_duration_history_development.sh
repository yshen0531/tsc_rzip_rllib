#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

: "${ID2A_SOURCE_REVISION:?set ID2A_SOURCE_REVISION to the 40-character implementation revision}"
: "${ID2A_OUTPUT:?set ID2A_OUTPUT to a new repository-local output directory}"

if [[ ! "$ID2A_SOURCE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "invalid ID2A_SOURCE_REVISION" >&2
  exit 2
fi
if [[ "$ID2A_OUTPUT" != "$ROOT"/* ]] || [[ -e "$ID2A_OUTPUT" ]]; then
  echo "ID2A_OUTPUT must be a new path inside the repository" >&2
  exit 2
fi

set +e
python scripts/rgeo_zgeo_1ms_id2a_duration_history_development.py run \
  --source-revision "$ID2A_SOURCE_REVISION" \
  --output "$ID2A_OUTPUT"
PRIMARY_RC=$?
set -e

if python - "$ID2A_OUTPUT/result.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
raise SystemExit(0 if d.get("execution_passed") and d.get("raw_integrity_passed") else 1)
PY
then
  set +e
  python scripts/rgeo_zgeo_1ms_id2a_duration_history_development_independent.py \
    --source-revision "$ID2A_SOURCE_REVISION" \
    --run-dir "$ID2A_OUTPUT"
  AUDIT_RC=$?
  set -e
  if [[ "$AUDIT_RC" -ne 0 ]]; then
    exit 2
  fi
fi

exit "$PRIMARY_RC"
