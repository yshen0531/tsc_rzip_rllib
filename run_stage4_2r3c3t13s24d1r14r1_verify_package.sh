#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R1_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
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
    "stage": "Stage4.2R3c3T13S24D1R14R1",
    "run_name": "stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight",
    "campaign_identity": "pooled_whitened_amplified_mixed_basis_preflight_v1",
    "controller_revision": "none_zero_tsc_static_preflight",
    "package_revision": "r42r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1",
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
actual = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual.append(path.relative_to(root).as_posix())
listed_tree = [item for item in listed if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
required = {
    "AGENTS.md",
    "configs/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1.json",
    "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R1_POOLED_MIXED_BASIS_PREFLIGHT_DESIGN.md",
    "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight.py",
    "run_stage4_2r3c3t13s24d1r14r1_common.sh",
    "run_stage4_2r3c3t13s24d1r14r1_offline.sh",
    "run_stage4_2r3c3t13s24d1r14r1_verify_package.sh",
    "scripts/stage4_2r3c3t13s24d1r14r1_shell_common.sh",
    "tests/test_stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight.py",
    "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s24d1r14_zero_baseline_signed_excitation_sentinel.py",
}
if not required.issubset(set(listed)):
    raise SystemExit(f"D1R14R1 required package files missing: {sorted(required - set(listed))}")
for path in sorted(root.rglob("*.py")):
    if any(part.endswith("_runs") or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"} for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight as r1
config = root / "configs/stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1.json"
cfg = json.loads(config.read_text(encoding="utf-8"))
r1._validate_design(cfg)
design = root / cfg["design_document"]
if r1._sha256(design) != cfg["design_document_sha256"]:
    raise SystemExit("D1R14R1 design-document hash mismatch")
print("[T13S24D1R14R1 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v tests.test_stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight
printf '[T13S24D1R14R1 verify] checksums, shell syntax and focused tests passed.\n'
