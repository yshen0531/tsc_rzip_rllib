#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
PYTHON_BIN="${STAGE4_1R12_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON:-python3}"
fi
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1 && [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: no executable Python found: ${PYTHON_BIN}" >&2
  exit 1
fi
for path in configs scripts tests tsc_rzip_rllib; do
  [[ -d "${path}" ]] || { echo "ERROR: required directory missing: ${path}" >&2; exit 1; }
done
for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json \
  configs/stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json \
  configs/stage4_1r10_queue_preview_terminal_transition_hold_750ms.json \
  scripts/stage4_1r12_original_deadline_weak_slew_anticipatory_damping.py \
  scripts/stage4_1r12_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r12_original_deadline_weak_slew_anticipatory_damping.py \
  tsc_rzip_rllib/diagnostics/stage4_1r3_control_aware_robustness.py \
  tests/test_stage4_1r12_original_deadline_weak_slew_anticipatory_damping.py \
  run_stage4_1r12_original_deadline_weak_slew_anticipatory_damping_native.sh \
  run_stage4_1r12_original_deadline_weak_slew_anticipatory_damping_nohup.sh \
  run_stage4_1r12_self_test.sh \
  run_stage4_1r12_verify_package.sh \
  run_stop_stage4_1r12_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r12"* ]] || {
    echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2
    exit 1
  }
done
find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.1R12 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
expected = {
    "stage": "Stage4.1R12",
    "controller_revision": "original_deadline_weak_slew_anticipatory_damping_v12",
    "package_revision": "r12_original_deadline_post_arrival_damping_v4",
    "run_name": "stage4_1r12_original_deadline_weak_slew_anticipatory_damping",
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f"PACKAGE_MANIFEST {key} mismatch: {manifest.get(key)!r} != {value!r}")

checksum_rows = [
    line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
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

# Every file under the replaced code directories must be declared. Residual
# Markdown, logs, zips and run outputs elsewhere in the server project are not
# package inputs and are intentionally ignored.
actual_replaced = []
for directory in ("configs", "scripts", "tests", "tsc_rzip_rllib"):
    for path in sorted((root / directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            actual_replaced.append(str(path.relative_to(root)))
listed_replaced = [
    item for item in listed if item.split("/", 1)[0] in {"configs", "scripts", "tests", "tsc_rzip_rllib"}
]
if actual_replaced != listed_replaced:
    missing = sorted(set(actual_replaced) - set(listed_replaced))
    extra = sorted(set(listed_replaced) - set(actual_replaced))
    raise SystemExit(f"replaced-tree inventory mismatch missing={missing[:20]} extra={extra[:20]}")

ignored_roots = {
    "stage2_runs", "stage3_runs", "stage3_4_runs", "stage4_runs",
    "stage4_1r6_runs", "stage4_1r7_runs", "stage4_1r8_runs",
    "stage4_1r9_runs", "stage4_1r10_runs", "stage4_1r11_runs",
    "stage4_1r12_runs", "logs", "__pycache__",
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
# dependencies such as Ray, gymnasium or the server TSC bindings.
module_by_path = {}
modules = set()
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

missing = []
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

from tsc_rzip_rllib.diagnostics import stage4_1r12_original_deadline_weak_slew_anticipatory_damping as r12
from tsc_rzip_rllib.diagnostics import stage4_1r3_control_aware_robustness as r3
payload = r12.self_test(root)
if not payload.get("passed"):
    raise SystemExit("Stage4.1R12 self-test failed")
if payload.get("package_revision") != expected["package_revision"]:
    raise SystemExit("Stage4.1R12 self-test package revision mismatch")
if payload.get("candidate_first_affected_state_steps") != [28, 30, 32, 33, 34, 35]:
    raise SystemExit("R12 post-arrival first-effect candidate bank mismatch")
if not payload.get("post_deadline_first_effect_only"):
    raise SystemExit("R12 candidate may affect physics by/before 270 ms")
if not payload.get("no_arrival_deadline_expansion"):
    raise SystemExit("R12 deadline expansion guard failed")
if payload.get("maximum_true_tsc_rollouts") != 18:
    raise SystemExit("R12 true-TSC campaign budget mismatch")
if not payload.get("stage4_2r1_was_not_run_or_reused"):
    raise SystemExit("R12 must not claim or reuse unrun Stage4.2R1")

cfg = json.loads(
    (root / "configs/stage4_1r12_original_deadline_weak_slew_anticipatory_damping_370ms.json")
    .read_text(encoding="utf-8")
)
r12.validate_config(cfg)
normal = cfg["formal_timing_contract"]["normal_slew"]
weak = cfg["formal_timing_contract"]["weak_slew"]
closure = cfg["weak_slew_closure"]
if (normal["arrival_deadline_step"], normal["horizon_steps"]) != (25, 35):
    raise SystemExit("normal 250/350 ms contract changed")
if (weak["arrival_deadline_step"], weak["horizon_steps"]) != (27, 37):
    raise SystemExit("weak 270/370 ms contract changed")
if max(normal["allowed_arrival_steps"]) != 25 or max(weak["allowed_arrival_steps"]) != 27:
    raise SystemExit("formal arrival list exceeds immutable deadline")
if closure["actual_delay_steps"] != [1, 2] or closure["actual_slew_scale"] != 0.9:
    raise SystemExit("R12 scope expanded beyond four weak-slew delay=1/2 cases")
if closure["candidate_first_affected_state_steps"] != [28, 30, 32, 33, 34, 35]:
    raise SystemExit("R12 candidate bank changed")
if min(closure["candidate_first_affected_state_steps"]) <= weak["arrival_deadline_step"]:
    raise SystemExit("R12 candidate first effect is not strictly after 270 ms")
if closure.get("modified_paths_may_change_before_arrival_deadline"):
    raise SystemExit("R12 allows source physics to change before/by 270 ms")
if not closure.get("preserve_source_physics_through_arrival_deadline"):
    raise SystemExit("R12 does not preserve source physics through 270 ms")
if cfg.get("stage4_2r1_was_not_run_or_reused") is not True:
    raise SystemExit("R12 Stage4.2R1 provenance guard failed")
if cfg["calibrated_confirmation"].get("online_handover_enabled"):
    raise SystemExit("R12 unexpectedly enables online handover")

r3_source = (root / "tsc_rzip_rllib/diagnostics/stage4_1r3_control_aware_robustness.py").read_text(encoding="utf-8")
for token in (
    "_stage4_1r12_main_control_stop_step",
    "partial_main_control_checkpoint",
    "main_control_stop_step = 35 if partial_stop_step is None",
):
    if token not in r3_source:
        raise SystemExit(f"R3 partial-checkpoint hook missing: {token}")

campaign = manifest.get("campaign") or {}
if campaign.get("oracle_development_rollouts") != 12:
    raise SystemExit("manifest development campaign mismatch")
if campaign.get("oracle_holdout_rollouts_if_development_passes") != 2:
    raise SystemExit("manifest holdout campaign mismatch")
if campaign.get("calibrated_confirmation_rollouts_if_holdout_passes") != 4:
    raise SystemExit("manifest calibrated campaign mismatch")
if campaign.get("maximum_real_tsc_episodes") != 18:
    raise SystemExit("manifest real-TSC budget mismatch")
print("[Stage4.1R12 verify] Python compile, JSON parse, internal import closure and formal scientific guardrails passed.")
PY
while IFS= read -r script; do
  bash -n "${script}"
done < <(awk '{print $2}' SHA256SUMS | grep -E '\.sh$' | sort -u)
printf '[Stage4.1R12 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test*.py'
printf '[Stage4.1R12 verify] complete unittest discovery passed.\n'
printf '[Stage4.1R12 verify] residual Markdown, archives, logs and run outputs outside SHA256SUMS are intentionally ignored.\n'
