#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T2_PYTHON:-${PYTHON:-python3}}"
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
    "stage": "Stage4.2R3c3T2",
    "controller_revision": (
        "post_contract_neutralized_held_transport_probe_v42r3c3t2_v2"
    ),
    "package_revision": (
        "r42r3c3t2_post_contract_held_transport_identification_v2h1"
    ),
    "run_name": (
        "stage4_2r3c3t2_post_contract_neutralized_held_transport_"
        "identification"
    ),
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
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)

cfg, _ = t2._resolved_config(
    root
    / "configs/stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_500ms.json"
)
if not t2.self_test()["passed"]:
    raise SystemExit("T2 self-test failed")
if (
    cfg["control_matrix"]["expected_rollouts"] != 160
    or cfg["identification_probe"]["observation_horizon_steps"] != 50
    or cfg["formal_timing_contract"]["normal"]["hold_through_step"]
    != 35
    or cfg["formal_timing_contract"]["weak"]["hold_through_step"]
    != 37
):
    raise SystemExit("T2 scientific guard changed")
for path in (
    root
    / "run_stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_native.sh",
    root / "run_stop_stage4_2r3c3t2_now.sh",
):
    text = path.read_text(encoding="utf-8")
    if "ray stop --force" in text or "pkill" in text:
        raise SystemExit("broad process termination is forbidden")
print("[Stage4.2R3c3T2 verify] Python/JSON/scientific guards passed.")
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
"${PYTHON_BIN}" - <<'PY'
import unittest
import tests.conftest
suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_stage4_2r3c3t2_post_contract_neutralized_held_transport_identification"
)
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
printf '[Stage4.2R3c3T2 verify] checksums, shell syntax and focused tests passed.\n'
