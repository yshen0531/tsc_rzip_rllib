#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R7_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python missing" >&2; exit 1; }
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON_BIN}" - <<'PY'
import json
from pathlib import Path

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r7_independent_forensics as independent
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight as stage

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected_manifest = {
    "stage": "Stage4.2R3c3T13S24D1R7",
    "campaign_identity": "temporal_basis_substitution_preflight_v1",
    "package_revision": "r42r3c3t13s24d1r7_temporal_basis_substitution_preflight_v1h1",
    "implementation_checkpoint": "da578de",
}
for key, expected in expected_manifest.items():
    if manifest.get(key) != expected:
        raise SystemExit(f"D1R7 manifest {key} mismatch")
execution = manifest.get("execution_contract", {})
if execution.get("new_raw_count") != 0 or any(
    execution.get(key) is not False
    for key in ("ray_executed", "gotsc_executed", "tsc_executed", "controller_executed")
):
    raise SystemExit("D1R7 manifest zero-execution contract mismatch")
config_path = root / manifest["config_path"]
config = json.loads(config_path.read_text(encoding="utf-8"))
stage._validate_config(config, config_path)
matrix = stage.requested_matrix(config)
metrics = stage.matrix_metrics(matrix, config)
if independent.STAGE != stage.STAGE or not metrics["global_pass"]:
    raise SystemExit("D1R7 scientific package guard failed")
for relative in manifest["file_inventory"]:
    path = root / relative
    if path.suffix == ".py":
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    elif path.suffix == ".json":
        json.loads(path.read_text(encoding="utf-8"))
print("[T13S24D1R7 verify] Python/JSON/scientific guards passed")
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r7_temporal_basis_substitution_preflight
printf '[T13S24D1R7 verify] checksums, shell syntax, compile, JSON and focused tests passed\n'
