#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R7_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
tr -d '\r' < SHA256SUMS | sha256sum -c -
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
import ast
import json
from pathlib import Path
root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S24D1R14R7",
    "identity": "causal_deconfounded_response_model_development_v1",
    "package_revision": "r42r3c3t13s24d1r14r7_causal_response_model_v1",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
listed = [line.split(None, 1)[1].strip() for line in rows]
if listed != manifest.get("file_inventory") or listed != sorted(set(listed)) or len(listed) != manifest.get("declared_file_count"):
    raise SystemExit("package inventory mismatch")
required = {
    "configs/stage4_2r3c3t13s24d1r14r7_causal_response_model_v1.json",
    "tsc_rzip_rllib/control/causal_response_model.py",
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7_causal_response_model.py",
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r7_independent_forensics.py",
    "tests/test_stage4_2r3c3t13s24d1r14r7_causal_response_model.py",
}
if not required.issubset(set(listed)):
    raise SystemExit(f"R7 required files missing: {sorted(required - set(listed))}")
for path in sorted(root.rglob("*.py")):
    if any(part.endswith("_runs") or part.endswith("_audits") or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"} for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_causal_response_model as primary
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_independent_forensics as independent
cfg = json.loads((root / "configs/stage4_2r3c3t13s24d1r14r7_causal_response_model_v1.json").read_text(encoding="utf-8"))
primary._validate_config(cfg)
independent._validate_frozen_contract(cfg)
print("[T13S24D1R14R7 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v tests.test_stage4_2r3c3t13s24d1r14r7_causal_response_model
printf '[T13S24D1R14R7 verify] checksums, shell syntax and focused tests passed.\n'
