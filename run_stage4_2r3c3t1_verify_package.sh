#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R3C3T1_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_370ms.json \
  scripts/stage4_2r3c3t1_long_separation_zero_net_transport_identification.py \
  scripts/stage4_2r3c3t1_server_postprocess.py \
  scripts/stage4_2r3c3t1_shell_common.sh \
  scripts/stage4_2r3c3_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3t1_long_separation_zero_net_transport_identification.py \
  tsc_rzip_rllib/diagnostics/stage4_2r3c3_restart_task_clock_local_response_identification.py \
  tests/test_stage4_2r3c3t1_long_separation_zero_net_transport_identification.py \
  run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_native.sh \
  run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_nohup.sh \
  run_stage4_2r3c3t1_server_postprocess.sh \
  run_stage4_2r3c3t1_self_test.sh \
  run_stage4_2r3c3t1_verify_package.sh \
  run_stop_stage4_2r3c3t1_now.sh; do
  [[ -f "${path}" ]] || {
    echo "ERROR: required packaged file missing: ${path}" >&2
    exit 1
  }
done

sha256sum -c SHA256SUMS
printf '[Stage4.2R3c3T1 verify] packaged file checksums passed.\n'
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
    "stage": "Stage4.2R3c3T1",
    "controller_revision": (
        "long_separation_zero_net_transport_probe_v42r3c3t1"
    ),
    "package_revision": (
        "r42r3c3t1_long_separation_transport_identification_v1"
    ),
    "run_name": (
        "stage4_2r3c3t1_long_separation_zero_net_transport_identification"
    ),
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(
            f"PACKAGE_MANIFEST {key} mismatch: {manifest.get(key)!r}"
        )
rows = [
    line
    for line in (root / "SHA256SUMS").read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]
listed = [line.split(None, 1)[1].strip() for line in rows]
if len(rows) != manifest.get("declared_file_count"):
    raise SystemExit("declared file count mismatch")
if listed != manifest.get("file_inventory"):
    raise SystemExit("manifest inventory differs from SHA256SUMS")
if listed != sorted(set(listed)):
    raise SystemExit("inventory must be sorted and unique")
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
    raise SystemExit(
        "replaced-tree inventory mismatch "
        f"missing={sorted(set(actual)-set(listed_tree))[:10]} "
        f"extra={sorted(set(listed_tree)-set(actual))[:10]}"
    )

for path in sorted(root.rglob("*.py")):
    if any(
        part.endswith("_runs")
        or part in {
            "logs",
            "__pycache__",
            "artifacts",
            ".codex_tmp",
        }
        for part in path.parts
    ):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))

modules = set()
module_by_path = {}
for path in sorted((root / "tsc_rzip_rllib").rglob("*.py")):
    module = (
        ".".join(path.parent.relative_to(root).parts)
        if path.name == "__init__.py"
        else ".".join(path.relative_to(root).with_suffix("").parts)
    )
    modules.add(module)
    module_by_path[path] = module


def resolve(package: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    parts = package.split(".") if package else []
    drop = level - 1
    if drop > len(parts):
        raise SystemExit("invalid relative import")
    parts = parts[: len(parts) - drop]
    if module:
        parts.extend(module.split("."))
    return ".".join(parts)


missing = []
for path, module in module_by_path.items():
    package = (
        module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("tsc_rzip_rllib") and not any(
                    name == candidate
                    or name.startswith(candidate + ".")
                    for candidate in modules
                ):
                    missing.append((str(path), name))
        elif isinstance(node, ast.ImportFrom):
            base = resolve(package, node.level, node.module)
            if (
                base.startswith("tsc_rzip_rllib")
                and base not in modules
                and not any(
                    candidate.startswith(base + ".")
                    for candidate in modules
                )
            ):
                missing.append((str(path), base))
if missing:
    raise SystemExit(
        "missing packaged internal imports: " + repr(missing[:20])
    )

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t1_long_separation_zero_net_transport_identification as t1,
)

cfg = json.loads(
    (
        root
        / "configs/stage4_2r3c3t1_long_separation_zero_net_transport_identification_370ms.json"
    ).read_text(encoding="utf-8")
)
t1.validate_config(cfg)
if not t1.self_test().get("passed"):
    raise SystemExit("Stage4.2R3c3T1 self-test failed")
if t1.r3c3._phase_trace_valid is t1._phase_trace_valid:
    raise SystemExit("frozen R3c3 phase validator was mutated")
if t1._requested_workers(cfg) != 128:
    raise SystemExit("Stage4.2R3c3T1 Ray capacity changed")
probe = cfg["identification_probe"]
if (
    probe["physical_mode_amplitude"] != [0.0075, 0.0075, 0.0]
    or len(probe["basis"]) != 2
    or probe["required_nonzero_issue_count"] != 12
    or probe["probe_signs"] != [-1, 1]
    or not probe["require_requested_and_applied_zero_net"]
    or probe["formal_tracking_pass_required"]
    or probe["probe_trajectories_allowed_in_expert_dataset"]
):
    raise SystemExit("identification-probe contract changed")
matrix = cfg["control_matrix"]
if (
    matrix["expected_rollouts"] != 128
    or matrix["expected_baseline_contexts"] != 32
    or matrix["probe_basis_count"] != 2
):
    raise SystemExit("control matrix changed")
contract = cfg["formal_timing_contract"]
if (
    contract["normal"]["arrival_deadline_step"] != 25
    or contract["normal"]["hold_through_step"] != 35
    or contract["weak"]["arrival_deadline_step"] != 27
    or contract["weak"]["hold_through_step"] != 37
    or contract["arrival_deadline_expansion_allowed"]
):
    raise SystemExit("immutable formal timing changed")
if (
    not cfg["development_set_only"]
    or cfg["independent_hidden_history_confirmation"]
    or cfg["bc_dagger_or_rl_allowed"]
):
    raise SystemExit("scientific scope changed")
source = cfg["source_requirements"]
if (
    source["required_stage4_2r3c3_raw_inventory_digest"]
    != "88bcd02a5dd2ec4def60c1f2e7f2304fb57859836d3b9a34b090bfd91e00e563"
    or source["required_stage4_2r3c3_bank_provenance_digest"]
    != "5ec49166e59df915105d4411df36a9901db56f365594b83ff08bbc6abf3751f6"
):
    raise SystemExit("source R3c3 response evidence changed")
module = (
    root
    / "tsc_rzip_rllib/diagnostics/"
    "stage4_2r3c3t1_long_separation_zero_net_transport_identification.py"
).read_text(encoding="utf-8")
for token in (
    "LongSeparationTransportProbeController",
    "expected_count == 12",
    "_summarize_transport_responses",
    "combined_condition_number_gate_passed",
    "probe_trajectories_allowed_in_expert_dataset",
    "bc_dagger_or_rl_allowed",
):
    if token not in module:
        raise SystemExit(f"implementation guard missing: {token}")
for path in (
    root
    / "run_stage4_2r3c3t1_long_separation_zero_net_transport_identification_native.sh",
    root / "run_stop_stage4_2r3c3t1_now.sh",
):
    text = path.read_text(encoding="utf-8")
    if "ray stop --force" in text or "pkill" in text:
        raise SystemExit("launcher contains broad process termination")
print(
    "[Stage4.2R3c3T1 verify] Python compile, JSON parse, import closure "
    "and scientific guardrails passed."
)
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
printf '[Stage4.2R3c3T1 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" - <<'PY'
import unittest

import tests.conftest

suite = unittest.defaultTestLoader.loadTestsFromName(
    "tests.test_stage4_2r3c3t1_long_separation_zero_net_transport_identification"
)
result = unittest.TextTestRunner(verbosity=1).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
printf '[Stage4.2R3c3T1 verify] focused unittests passed.\n'
