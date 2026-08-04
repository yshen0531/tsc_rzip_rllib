#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S24D1R14R8_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
[[ -x "${PYTHON_BIN}" ]] || { echo "ERROR: server virtualenv Python not executable" >&2; exit 1; }
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.2R3c3T13S24D1R14R8",
    "run_name": "stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification",
    "campaign_identity": "partitioned_broad_deconfounded_response_identification_v1",
    "controller_revision": "inherited_exact_card15_issue_cancel_v42r3c3t13s24d1r14r8_v1",
    "package_revision": "r42r3c3t13s24d1r14r8_partitioned_broad_response_identification_v1",
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
listed_tree = [name for name in listed if name.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
for name in listed:
    path = root / name
    if path.suffix == ".py":
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
from tsc_rzip_rllib.diagnostics import stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8
config = root / "configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json"
r8._validate_config(json.loads(config.read_text(encoding="utf-8")), config)
if not r8.self_test(config)["passed"]:
    raise SystemExit("R8 self-test failed")
print("[R8 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m unittest -v \
  tests.test_stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel \
  tests.test_stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification
printf '[R8 verify] checksums, shell syntax and focused tests passed.\n'
