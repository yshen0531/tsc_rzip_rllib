#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T9_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"
sha256sum -c SHA256SUMS
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads(
    (root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
)
expected = {
    "stage": "Stage4.2R3c3T9",
    "controller_revision": "pc3_mixed_interaction_probe_v42r3c3t9_v1",
    "package_revision": "r42r3c3t9_pc3_mixed_interaction_identification_v1h1",
    "run_name": "stage4_2r3c3t9_pc3_mixed_interaction_identification",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch")
rows = [
    line
    for line in (root / "SHA256SUMS").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]
listed = [line.split(None, 1)[1].strip() for line in rows]
if (
    listed != manifest.get("file_inventory")
    or len(listed) != manifest.get("declared_file_count")
    or listed != sorted(set(listed))
):
    raise SystemExit("package inventory mismatch")
actual = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        ):
            actual.append(path.relative_to(root).as_posix())
listed_tree = [
    item
    for item in listed
    if item.split("/", 1)[0]
    in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual != listed_tree:
    raise SystemExit("replaced-tree inventory mismatch")
for path in sorted(root.rglob("*.py")):
    if any(
        part.endswith("_runs")
        or part
        in {"logs", "__pycache__", "artifacts", ".codex_tmp"}
        for part in path.parts
    ):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t9_pc3_mixed_interaction_identification as t9,
)

if not t9.self_test()["passed"]:
    raise SystemExit("T9 self-test failed")
cfg = json.loads(
    (
        root
        / "configs/stage4_2r3c3t9_pc3_mixed_interaction_identification_500ms.json"
    ).read_text(encoding="utf-8")
)
t9._validate_config(cfg)
for path in (
    root
    / "run_stage4_2r3c3t9_pc3_mixed_interaction_identification_native.sh",
    root / "run_stop_stage4_2r3c3t9_now.sh",
):
    text = path.read_text(encoding="utf-8")
    if "ray stop --force" in text or "pkill" in text:
        raise SystemExit("broad process termination is forbidden")
print("[Stage4.2R3c3T9 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
"${PYTHON_BIN}" -m unittest \
  tests.test_stage4_2r3c3t9_pc3_mixed_interaction_preflight \
  tests.test_stage4_2r3c3t9_pc3_mixed_interaction_identification
printf '[Stage4.2R3c3T9 verify] checksums, shell syntax and focused tests passed.\n'
