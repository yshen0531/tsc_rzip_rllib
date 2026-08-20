#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 2

SOURCE_REVISION="${ID2Z28_SOURCE_REVISION:?ID2Z28_SOURCE_REVISION is required}"
OUTPUT="${ID2Z28_OUTPUT:?ID2Z28_OUTPUT is required}"
CONFIG="$ROOT/configs/rgeo_zgeo_1ms_id2z28_event_value_model.json"
PRIMARY="$OUTPUT/result.json"
AUDIT="$OUTPUT/independent_audit.json"

if [[ -e "$OUTPUT" ]]; then
  echo "ID2Z28 output already exists: $OUTPUT" >&2
  exit 2
fi
mkdir -p "$OUTPUT" || exit 2

python "$ROOT/scripts/rgeo_zgeo_1ms_id2z28_event_value_model.py" \
  --config "$CONFIG" \
  --source-revision "$SOURCE_REVISION" \
  --output "$PRIMARY"
primary_rc=$?
if [[ "$primary_rc" -ne 0 && "$primary_rc" -ne 2 ]]; then
  echo "ID2Z28 primary process failed with rc=$primary_rc" >&2
  exit 2
fi

python "$ROOT/scripts/rgeo_zgeo_1ms_id2z28_event_value_model_independent.py" \
  --config "$CONFIG" \
  --primary "$PRIMARY" \
  --source-revision "$SOURCE_REVISION" \
  --output "$AUDIT"
audit_rc=$?
if [[ "$audit_rc" -ne 0 ]]; then
  exit 2
fi

# A preregistered scientific FAIL is a valid completed audit.  Preserve the
# primary return code in a separate file without converting it to workflow
# failure or PASS.
printf '%s\n' "$primary_rc" > "$OUTPUT/primary_exit_code.txt"
exit 0
