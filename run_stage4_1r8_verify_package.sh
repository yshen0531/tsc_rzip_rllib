#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"
PYTHON_BIN="${STAGE4_1R8_PYTHON:-/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="${PYTHON:-python3}"
fi
[[ -x "$(command -v "${PYTHON_BIN}" 2>/dev/null || true)" || -x "${PYTHON_BIN}" ]] || {
  echo "ERROR: no executable Python found: ${PYTHON_BIN}" >&2
  exit 1
}
for path in configs scripts tests tsc_rzip_rllib; do
  [[ -d "${path}" ]] || { echo "ERROR: required directory missing: ${path}" >&2; exit 1; }
done
for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_1r8_trusted_batch_calibration_queue_tail_closure_410ms.json \
  scripts/stage4_1r8_trusted_batch_calibration_queue_tail_closure.py \
  scripts/stage4_1r8_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r8_trusted_batch_calibration_queue_tail_closure.py \
  tests/test_stage4_1r8_trusted_batch_calibration_queue_tail_closure.py \
  run_stage4_1r8_trusted_batch_calibration_queue_tail_closure_native.sh \
  run_stage4_1r8_trusted_batch_calibration_queue_tail_closure_nohup.sh \
  run_stage4_1r8_self_test.sh \
  run_stop_stage4_1r8_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
sha256sum -c SHA256SUMS
printf '[Stage4.1R8 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import json
from pathlib import Path
root = Path.cwd()
manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
if manifest.get("stage") != "Stage4.1R8":
    raise SystemExit("PACKAGE_MANIFEST stage mismatch")
if manifest.get("controller_revision") != "trusted_batch_calibration_queue_tail_closure_v8":
    raise SystemExit("PACKAGE_MANIFEST controller revision mismatch")
checksum_rows = [line for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines() if line.strip()]
if len(checksum_rows) != int(manifest.get("declared_file_count", -1)):
    raise SystemExit(f"declared file count mismatch: sums={len(checksum_rows)} manifest={manifest.get('declared_file_count')}")
for path in sorted(root.rglob("*.py")):
    if any(part in {"stage2_runs", "stage3_runs", "stage4_runs", "stage4_1r7_runs", "stage4_1r8_runs", "logs"} for part in path.parts):
        continue
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
for path in sorted((root / "configs").glob("*.json")):
    json.loads(path.read_text(encoding="utf-8"))
json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
from tsc_rzip_rllib.diagnostics import stage4_1r8_trusted_batch_calibration_queue_tail_closure as r8
payload = r8.self_test()
if not payload.get("passed"):
    raise SystemExit("Stage4.1R8 self-test failed")
print("[Stage4.1R8 verify] Python source compile, JSON parse, import closure and self-test passed.")
PY
while IFS= read -r script; do
  bash -n "${script}"
done < <(awk '{print $2}' SHA256SUMS | grep -E '\.sh$' | sort -u)
printf '[Stage4.1R8 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test*.py'
printf '[Stage4.1R8 verify] complete unittest discovery passed.\n'
printf '[Stage4.1R8 verify] residual Markdown or run-output files outside SHA256SUMS are intentionally ignored.\n'
