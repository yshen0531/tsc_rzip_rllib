#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R3_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
tr -d '\r' < SHA256SUMS | sha256sum -c -
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S24D1R14R3",
    "identity": "sign_split_response_feasibility_raw_audit_v1",
    "package_revision": "r42r3c3t13s24d1r14r3_sign_split_response_feasibility_v2_source_hash_hotfix",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
listed = [line.split(None, 1)[1].strip() for line in rows]
if listed != manifest.get("file_inventory") or listed != sorted(set(listed)):
    raise SystemExit("package inventory mismatch")
if len(listed) != manifest.get("declared_file_count"):
    raise SystemExit("declared file count mismatch")
required = {
    "configs/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_v1.json",
    "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SIGN_SPLIT_RESPONSE_FEASIBILITY_DESIGN.md",
    "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SOURCE_STATE_HASH_ERRATUM.md",
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r3_independent_forensics.py",
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility.py",
    "tests/test_stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility.py",
    "scripts/stage4_2r3c3t13s24d1r14r3_shell_common.sh",
    "run_stage4_2r3c3t13s24d1r14r3_common.sh",
    "run_stage4_2r3c3t13s24d1r14r3_offline.sh",
    "run_stage4_2r3c3t13s24d1r14r3_verify_package.sh",
}
if not required.issubset(set(listed)):
    raise SystemExit(f"D1R14R3 required files missing: {sorted(required - set(listed))}")
for path in sorted(root.rglob("*.py")):
    if any(part.endswith("_runs") or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"} for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
from tsc_rzip_rllib.diagnostics import stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility as r3
cfg_path = root / "configs/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_v1.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
r3._validate_config(cfg, root, root / cfg["design_document"])
print("[T13S24D1R14R3 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v tests.test_stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility
printf '[T13S24D1R14R3 verify] checksums, shell syntax and focused tests passed.\n'
