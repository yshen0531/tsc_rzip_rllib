#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T13S4_PYTHON:-${PYTHON:-python3}}"
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
    "stage": "Stage4.2R3c3T13S4",
    "run_name": "stage4_2r3c3t13s4_lattice_transition_holdout",
    "campaign_identity": "quantized_lattice_two_step_blind_holdout_v1",
    "controller_revision": "quantized_lattice_transition_probe_v42r3c3t13s4_v1",
    "package_revision": "r42r3c3t13s4_lattice_transition_holdout_v1",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
listed = [line.split(None, 1)[1].strip() for line in rows]
if listed != manifest.get("file_inventory") or listed != sorted(set(listed)):
    raise SystemExit("package inventory mismatch")
actual = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual.append(path.relative_to(root).as_posix())
listed_tree = [item for item in listed if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
for path in sorted(root.rglob("*.py")):
    if any(part.endswith("_runs") or part in {"logs", "__pycache__", "artifacts", ".codex_tmp"} for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
from tsc_rzip_rllib.diagnostics import stage4_2r3c3t13s4_lattice_transition_holdout as s4
if not s4.self_test()["passed"]:
    raise SystemExit("T13S4 self-test failed")
s4._validate_config(json.loads((root / "configs/stage4_2r3c3t13s4_lattice_transition_holdout_370ms.json").read_text()))
for path in (root / "run_stage4_2r3c3t13s4_native.sh", root / "run_stop_stage4_2r3c3t13s4_now.sh"):
    text = path.read_text(encoding="utf-8")
    if "ray stop --force" in text or "pkill" in text:
        raise SystemExit("broad process termination is forbidden")
print("[T13S4 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
"${PYTHON_BIN}" -m pytest -q tests/test_stage4_2r3c3t13s4_lattice_transition_holdout.py
printf '[T13S4 verify] checksums, shell syntax and focused tests passed.\n'
