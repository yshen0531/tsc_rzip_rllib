#!/usr/bin/env bash
set -euo pipefail

PROJECT="${HOME}/tsc_all/tsc_rzip_rllib"
VENV="${HOME}/tsc_all/tsc_simulation/venv_simu"
OUTPUT="${ID2Z19R1_ATTRIBUTION_OUTPUT:?ID2Z19R1_ATTRIBUTION_OUTPUT is required}"

test -d "$PROJECT"
test -f "$VENV/bin/activate"
cd "$PROJECT"
test "$PWD" = "$PROJECT"
source "$VENV/bin/activate"
python scripts/rgeo_zgeo_1ms_id2z19r1_zero_fit_attribution.py --output "$OUTPUT"

