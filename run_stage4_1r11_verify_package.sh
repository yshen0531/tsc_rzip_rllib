#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
PYTHON_BIN="${STAGE4_1R11_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
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
  configs/stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json \
  configs/stage4_1r10_queue_preview_terminal_transition_hold_750ms.json \
  scripts/stage4_1r11_frozen_terminal_long_horizon_hold.py \
  scripts/stage4_1r11_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r11_frozen_terminal_long_horizon_hold.py \
  tsc_rzip_rllib/diagnostics/stage4_1r10_queue_preview_terminal_transition_hold.py \
  tests/test_stage4_1r11_frozen_terminal_long_horizon_hold.py \
  run_stage4_1r11_frozen_terminal_long_horizon_hold_native.sh \
  run_stage4_1r11_frozen_terminal_long_horizon_hold_nohup.sh \
  run_stage4_1r11_self_test.sh \
  run_stage4_1r11_verify_package.sh \
  run_stop_stage4_1r11_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r11"* ]] || {
    echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2
    exit 1
  }
done
sha256sum -c SHA256SUMS
printf '[Stage4.1R11 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
if manifest.get("stage") != "Stage4.1R11":
    raise SystemExit("PACKAGE_MANIFEST stage mismatch")
if manifest.get("controller_revision") != "frozen_queue_preview_terminal_long_horizon_hold_v11":
    raise SystemExit("PACKAGE_MANIFEST controller revision mismatch")
if manifest.get("package_revision") != "r11_frozen_long_hold_v1":
    raise SystemExit("PACKAGE_MANIFEST package revision mismatch")
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

ignored_roots = {
    "stage2_runs", "stage3_runs", "stage4_runs", "stage4_1r7_runs",
    "stage4_1r8_runs", "stage4_1r9_runs", "stage4_1r10_runs",
    "stage4_1r11_runs", "logs", "__pycache__",
}
for path in sorted(root.rglob("*.py")):
    if any(part in ignored_roots for part in path.parts):
        continue
    source = path.read_text(encoding="utf-8")
    compile(source, str(path), "exec")
    ast.parse(source, filename=str(path))
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))

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

from tsc_rzip_rllib.diagnostics import stage4_1r11_frozen_terminal_long_horizon_hold as r11
payload = r11.self_test()
if not payload.get("passed"):
    raise SystemExit("Stage4.1R11 self-test failed")
if payload.get("package_revision") != "r11_frozen_long_hold_v1":
    raise SystemExit("Stage4.1R11 self-test package revision mismatch")
if not payload.get("r10_preview_queue_semantics_retained"):
    raise SystemExit("Stage4.1R11 inherited preview-queue regression failed")
if not payload.get("long_hold_metric_arithmetic_passed"):
    raise SystemExit("Stage4.1R11 long-hold arithmetic regression failed")

cfg = json.loads(
    (root / "configs/stage4_1r11_frozen_terminal_long_horizon_hold_2000ms.json")
    .read_text(encoding="utf-8")
)
r11.validate_config(cfg)
hold = cfg["long_hold"]
if hold["main_control_steps"] != 35 or hold["source_horizon_steps"] != 75:
    raise SystemExit("R11 frozen source-prefix boundary guard failed")
if hold["horizon_steps"] != 200 or hold["tail_feedback_steps"] != 165:
    raise SystemExit("R11 2000 ms horizon guard failed")
if hold["uniform_hold_start_step"] != 65:
    raise SystemExit("R11 fixed 650 ms hold-start guard failed")
if not hold.get("no_policy_retuning_allowed") or not hold.get("no_new_arrival_search_allowed"):
    raise SystemExit("R11 frozen-policy/no-endpoint-search guard failed")
if len(hold["targets"]) * len(hold["actual_delay_steps"]) * len(hold["actual_slew_scales"]) != 18:
    raise SystemExit("R11 18-case oracle/calibrated matrix guard failed")
if cfg["calibrated_confirmation"].get("online_handover_enabled"):
    raise SystemExit("R11 unexpectedly enables online handover")
print("[Stage4.1R11 verify] Python compile, JSON parse, complete internal import closure and scientific self-test passed.")
PY
while IFS= read -r script; do
  bash -n "${script}"
done < <(awk '{print $2}' SHA256SUMS | grep -E '\.sh$' | sort -u)
printf '[Stage4.1R11 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test*.py'
printf '[Stage4.1R11 verify] complete unittest discovery passed.\n'
printf '[Stage4.1R11 verify] residual Markdown and run-output files outside SHA256SUMS are intentionally ignored.\n'
