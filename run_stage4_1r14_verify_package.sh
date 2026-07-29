#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R14_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json \
  SHA256SUMS \
  configs/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json \
  scripts/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py \
  scripts/stage4_1r14_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py \
  tsc_rzip_rllib/diagnostics/stage4_1r13_original_deadline_delay_pipeline_early_braking.py \
  tests/test_stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py \
  tests/test_stage4_1r13_original_deadline_delay_pipeline_early_braking.py \
  tests/test_ray_runtime_capacity.py \
  run_stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_native.sh \
  run_stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_nohup.sh \
  run_stage4_1r14_self_test.sh \
  run_stage4_1r14_verify_package.sh \
  run_stop_stage4_1r14_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done

mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r14"* ]] || {
    echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2
    exit 1
  }
done

find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.1R14 verify] packaged file checksums passed.\n'

export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.1R14",
    "controller_revision": "original_deadline_integrated_target_conditioned_deadline_mpc_v14",
    "package_revision": "r14_integrated_target_conditioned_deadline_mpc_v1",
    "run_name": "stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(
            f"PACKAGE_MANIFEST {key} mismatch: {manifest.get(key)!r} != {value!r}"
        )

checksum_rows = [
    line
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(checksum_rows) != int(manifest.get("declared_file_count", -1)):
    raise SystemExit(
        f"declared file count mismatch: sums={len(checksum_rows)} "
        f"manifest={manifest.get('declared_file_count')}"
    )
listed = [line.split(None, 1)[1].strip() for line in checksum_rows]
if listed != manifest.get("file_inventory"):
    raise SystemExit("PACKAGE_MANIFEST file inventory differs from SHA256SUMS")
if listed != sorted(listed) or len(listed) != len(set(listed)):
    raise SystemExit("SHA256SUMS inventory is not sorted and unique")
if "PACKAGE_MANIFEST.json" not in listed:
    raise SystemExit("PACKAGE_MANIFEST.json is not checksum-protected")
if "SHA256SUMS" in listed:
    raise SystemExit("SHA256SUMS may not checksum itself")

actual_replaced: list[str] = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual_replaced.append(str(path.relative_to(root)))
listed_replaced = [
    item
    for item in listed
    if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual_replaced != listed_replaced:
    missing = sorted(set(actual_replaced) - set(listed_replaced))
    extra = sorted(set(listed_replaced) - set(actual_replaced))
    raise SystemExit(
        f"replaced-tree inventory mismatch missing={missing[:20]} extra={extra[:20]}"
    )

ignored_roots = {
    "stage2_runs",
    "stage3_runs",
    "stage3_4_runs",
    "stage4_runs",
    "stage4_1r6_runs",
    "stage4_1r7_runs",
    "stage4_1r8_runs",
    "stage4_1r9_runs",
    "stage4_1r10_runs",
    "stage4_1r11_runs",
    "stage4_1r12_runs",
    "stage4_1r13_runs",
    "stage4_1r14_runs",
    "logs",
    "__pycache__",
}
for path in sorted(root.rglob("*.py")):
    if any(part in ignored_roots for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))

# Resolve every packaged internal import without importing optional runtime
# dependencies such as Ray or the server TSC bindings.
module_by_path: dict[Path, str] = {}
modules: set[str] = set()
for path in sorted((root / "tsc_rzip_rllib").rglob("*.py")):
    if path.name == "__init__.py":
        module = ".".join(path.parent.relative_to(root).parts)
    else:
        module = ".".join(path.relative_to(root).with_suffix("").parts)
    module_by_path[path] = module
    modules.add(module)

def package_of(module: str, path: Path) -> str:
    return module if path.name == "__init__.py" else module.rsplit(".", 1)[0]

def resolve_from(current_package: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    parts = current_package.split(".") if current_package else []
    drop = level - 1
    if drop > len(parts):
        raise SystemExit(f"invalid relative import level={level} from {current_package}")
    parts = parts[: len(parts) - drop]
    if module:
        parts.extend(module.split("."))
    return ".".join(parts)

missing: list[tuple[str, str]] = []
for path, current_module in module_by_path.items():
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    current_package = package_of(current_module, path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("tsc_rzip_rllib") and not any(
                    name == candidate or name.startswith(candidate + ".")
                    for candidate in modules
                ):
                    missing.append((str(path), name))
        elif isinstance(node, ast.ImportFrom):
            base = resolve_from(current_package, node.level, node.module)
            if base.startswith("tsc_rzip_rllib") and base not in modules:
                if not any(candidate.startswith(base + ".") for candidate in modules):
                    missing.append((str(path), base))
if missing:
    raise SystemExit("missing packaged internal imports: " + repr(missing[:20]))

from tsc_rzip_rllib.diagnostics import (
    stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc as r14,
)

payload = r14.self_test(root)
if not payload.get("passed"):
    raise SystemExit("Stage4.1R14 self-test failed")
if payload.get("package_revision") != expected["package_revision"]:
    raise SystemExit("Stage4.1R14 self-test package revision mismatch")
if payload.get("fixed_first_affected_state_step") != 23:
    raise SystemExit("R14 must fix the R13 minimax onset at state 23")
if payload.get("candidate_count") != 6:
    raise SystemExit("R14 candidate-bank size mismatch")
if payload.get("development_rollout_count") != 24:
    raise SystemExit("R14 development campaign size mismatch")
if payload.get("maximum_true_tsc_rollouts") != 28:
    raise SystemExit("R14 true-TSC campaign budget mismatch")
if not payload.get("target_conditioned_nominal_required"):
    raise SystemExit("R14 target-conditioned nominal guard is disabled")
if not payload.get("checkpoint_integral_preservation_required"):
    raise SystemExit("R14 checkpoint-integral guard is disabled")
if payload.get("unseen_target_holdout_claimed"):
    raise SystemExit("R14 may not claim unseen-target generalization")
if not payload.get("stage4_2r1_was_not_run_or_reused"):
    raise SystemExit("R14 must not reuse unrun Stage4.2R1")

cfg = json.loads(
    (
        root
        / "configs/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc_370ms.json"
    ).read_text(encoding="utf-8")
)
r14.validate_config(cfg)
normal = cfg["formal_timing_contract"]["normal_slew"]
weak = cfg["formal_timing_contract"]["weak_slew"]
design = cfg["integrated_deadline_mpc"]
if (normal["arrival_deadline_step"], normal["horizon_steps"]) != (25, 35):
    raise SystemExit("normal 250/350 ms contract changed")
if (weak["arrival_deadline_step"], weak["horizon_steps"]) != (27, 37):
    raise SystemExit("weak 270/370 ms contract changed")
if max(normal["allowed_arrival_steps"]) != 25 or max(weak["allowed_arrival_steps"]) != 27:
    raise SystemExit("formal arrival list exceeds immutable deadline")
if design["actual_delay_steps"] != [1, 2] or design["actual_slew_scale"] != 0.9:
    raise SystemExit("R14 scope expanded beyond the four weak-slew delay=1/2 paths")
if design["fixed_first_affected_state_step"] != 23 or not design["require_no_onset_rescan"]:
    raise SystemExit("R14 onset was changed or rescanning is enabled")
if design["deadline_velocity_states"] != [24, 25, 26, 27]:
    raise SystemExit("R14 deadline-speed state set changed")
if not design["target_conditioned_nominal_physical_required"]:
    raise SystemExit("R14 target-conditioned feedforward is disabled")
if not design["target_conditioned_nominal_feature_required"]:
    raise SystemExit("R14 target-conditioned nominal trajectory is disabled")
if not design["checkpoint_integral_preservation_required"]:
    raise SystemExit("R14 checkpoint integral preservation is disabled")
if design["arrival_deadline_expansion_allowed"]:
    raise SystemExit("R14 arrival deadline expansion is enabled")
if not design["future_measurement_forbidden"]:
    raise SystemExit("R14 future-measurement guard is disabled")
if not design["unaffected_14_paths_remain_source_exact"]:
    raise SystemExit("R14 must retain the fourteen unaffected paths exactly")

module_text = (
    root
    / "tsc_rzip_rllib/diagnostics/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py"
).read_text(encoding="utf-8")
if 'interpolation["full_control_vector"]' not in module_text:
    raise SystemExit("R14 implementation does not restore target-conditioned feedforward")
if "nominal_physical = np.zeros((35" in module_text:
    raise SystemExit("R14 implementation reintroduced the R13 zero-nominal handoff")
if "integral = np.zeros(5" in module_text:
    raise SystemExit("R14 implementation reintroduced the R13 integral reset")

# Stage4.2R1 may only appear as an explicit not-run/not-reused guard.
for path in list((root / "scripts").rglob("*")) + list(
    (root / "tsc_rzip_rllib").rglob("*.py")
):
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    if "stage4_2r1" in text and not (
        "was_not_run_or_reused" in text
        or "was not run" in text
        or "not run" in text
    ):
        raise SystemExit(f"unexpected Stage4.2R1 operational dependency: {path}")

print(
    "[Stage4.1R14 verify] Python compile, JSON parse, internal import closure and formal scientific guardrails passed."
)
PY

mapfile -t SHELLS < <(
  {
    find . -maxdepth 1 -type f -name '*.sh' -print
    find scripts -type f -name '*.sh' -print
  } | sort -u
)
for script in "${SHELLS[@]}"; do
  bash -n "${script}"
done
printf '[Stage4.1R14 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test*.py'
printf '[Stage4.1R14 verify] complete unittest discovery passed.\n'
