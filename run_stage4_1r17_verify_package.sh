#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R17_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"
for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json \
  configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json \
  configs/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json \
  scripts/stage4_1r17_original_deadline_one_sided_robust_braking_closure.py \
  scripts/stage4_1r17_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r17_original_deadline_one_sided_robust_braking_closure.py \
  tsc_rzip_rllib/diagnostics/stage4_1r16_amplitude_certified_probe_derived_braking_closure.py \
  tsc_rzip_rllib/diagnostics/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation.py \
  tests/test_stage4_1r17_original_deadline_one_sided_robust_braking_closure.py \
  tests/test_ray_runtime_capacity.py \
  run_stage4_1r17_original_deadline_one_sided_robust_braking_closure_native.sh \
  run_stage4_1r17_original_deadline_one_sided_robust_braking_closure_nohup.sh \
  run_stage4_1r17_self_test.sh run_stage4_1r17_verify_package.sh \
  run_stop_stage4_1r17_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r17"* ]] || { echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2; exit 1; }
done
find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.1R17 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
expected = {
    'stage': 'Stage4.1R17',
    'controller_revision': 'original_deadline_one_sided_robust_braking_closure_v17',
    'package_revision': 'r17_delay_conditioned_one_sided_margin_closure_v1',
    'run_name': 'stage4_1r17_original_deadline_one_sided_robust_braking_closure',
}
for key, value in expected.items():
    if manifest.get(key) != value:
        raise SystemExit(f'PACKAGE_MANIFEST {key} mismatch: {manifest.get(key)!r}')
rows = [line for line in (root / 'SHA256SUMS').read_text(encoding='utf-8').splitlines() if line.strip()]
listed = [line.split(None, 1)[1].strip() for line in rows]
if len(rows) != manifest.get('declared_file_count'):
    raise SystemExit('declared file count mismatch')
if listed != manifest.get('file_inventory'):
    raise SystemExit('manifest inventory differs from SHA256SUMS')
if listed != sorted(set(listed)):
    raise SystemExit('inventory must be sorted and unique')
actual = []
for directory in ('configs', 'scripts', 'tests', 'tsc_rzip_rllib'):
    for path in sorted((root / directory).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            actual.append(str(path.relative_to(root)))
listed_tree = [item for item in listed if item.split('/', 1)[0] in {'configs', 'scripts', 'tests', 'tsc_rzip_rllib'}]
if actual != listed_tree:
    raise SystemExit(
        'replaced-tree inventory mismatch '
        f'missing={sorted(set(actual)-set(listed_tree))[:10]} '
        f'extra={sorted(set(listed_tree)-set(actual))[:10]}'
    )
ignored = {
    'stage2_runs', 'stage3_runs', 'stage3_4_runs', 'stage4_runs',
    'stage4_1r6_runs', 'stage4_1r7_runs', 'stage4_1r8_runs', 'stage4_1r9_runs',
    'stage4_1r10_runs', 'stage4_1r11_runs', 'stage4_1r12_runs', 'stage4_1r13_runs',
    'stage4_1r14_runs', 'stage4_1r15_runs', 'stage4_1r15b_runs', 'stage4_1r16_runs',
    'stage4_1r17_runs', 'logs', '__pycache__',
}
for path in sorted(root.rglob('*.py')):
    if any(part in ignored for part in path.parts):
        continue
    source = path.read_text(encoding='utf-8')
    compile(source, str(path), 'exec')
    ast.parse(source, filename=str(path))
for path in sorted((root / 'configs').glob('*.json')):
    json.loads(path.read_text(encoding='utf-8'))
modules = set()
module_by_path = {}
for path in sorted((root / 'tsc_rzip_rllib').rglob('*.py')):
    module = (
        '.'.join(path.parent.relative_to(root).parts)
        if path.name == '__init__.py'
        else '.'.join(path.relative_to(root).with_suffix('').parts)
    )
    modules.add(module)
    module_by_path[path] = module

def resolve(package: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ''
    parts = package.split('.') if package else []
    drop = level - 1
    if drop > len(parts):
        raise SystemExit('invalid relative import')
    parts = parts[: len(parts) - drop]
    if module:
        parts.extend(module.split('.'))
    return '.'.join(parts)

missing = []
for path, module in module_by_path.items():
    package = module if path.name == '__init__.py' else module.rsplit('.', 1)[0]
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith('tsc_rzip_rllib') and not any(
                    name == candidate or name.startswith(candidate + '.') for candidate in modules
                ):
                    missing.append((str(path), name))
        elif isinstance(node, ast.ImportFrom):
            base = resolve(package, node.level, node.module)
            if base.startswith('tsc_rzip_rllib') and base not in modules and not any(
                candidate.startswith(base + '.') for candidate in modules
            ):
                missing.append((str(path), base))
if missing:
    raise SystemExit('missing packaged internal imports: ' + repr(missing[:20]))

from tsc_rzip_rllib.diagnostics import stage4_1r17_original_deadline_one_sided_robust_braking_closure as r17

payload = r17.self_test(root)
if not payload.get('passed'):
    raise SystemExit('R17 self-test failed')
if payload.get('expected_true_tsc_oracle_rollouts') != 2:
    raise SystemExit('R17 Oracle rollout budget changed')
if payload.get('expected_true_tsc_calibrated_rollouts') != 4:
    raise SystemExit('R17 calibrated rollout budget changed')
if payload.get('maximum_true_tsc_rollouts') != 6:
    raise SystemExit('R17 maximum rollout budget changed')
if abs(float(payload.get('maximum_schedule_component')) - 0.105) > 1e-12:
    raise SystemExit('R17 maximum schedule component changed')
if payload.get('bidirectional_response_model_validated'):
    raise SystemExit('R17 may not claim bidirectional validation')

cfg = json.loads(
    (root / 'configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json').read_text(encoding='utf-8')
)
r17.validate_config(cfg)
if cfg['formal_timing_contract']['normal_slew']['arrival_deadline_step'] != 25:
    raise SystemExit('normal arrival deadline changed')
if cfg['formal_timing_contract']['weak_slew']['arrival_deadline_step'] != 27:
    raise SystemExit('weak arrival deadline changed')
candidate = cfg['one_sided_candidate']
if candidate['source_delay1_magnitude'] != 6.0 or candidate['new_delay2_magnitude'] != 7.0:
    raise SystemExit('R17 delay-conditioned magnitudes changed')
if candidate['direction_sign'] != -1 or candidate['peak_component'] != 0.105:
    raise SystemExit('R17 preregistered one-sided candidate changed')
if candidate['expected_oracle_rollouts'] != 2 or cfg['calibrated_confirmation']['expected_rollouts'] != 4:
    raise SystemExit('R17 task matrix changed')
if candidate['minimum_actual_signed_margin'] < 0.01:
    raise SystemExit('R17 actual margin guard weakened')
if not candidate['require_exact_per_step_probe_application']:
    raise SystemExit('R17 exact per-step probe guard disabled')
if not cfg['finite_test_envelope_only'] or cfg['bidirectional_response_model_validated']:
    raise SystemExit('R17 finite one-sided semantics changed')
if not cfg['stage4_2r1_was_not_run_or_reused']:
    raise SystemExit('R17 may not reuse Stage4.2R1')
module = (
    root / 'tsc_rzip_rllib/diagnostics/stage4_1r17_original_deadline_one_sided_robust_braking_closure.py'
).read_text(encoding='utf-8')
for token in (
    'per_step_probe_application_exact',
    'source_candidate_exact_failure',
    'source_only_robust_prediction_pass',
    'new_delay2_magnitude',
    'formal_grid_confirmation',
    'bidirectional_response_model_validated',
    'stage4_2r1_was_not_run_or_reused',
):
    if token not in module:
        raise SystemExit(f'R17 implementation guard missing: {token}')
print('[Stage4.1R17 verify] Python compile, JSON parse, internal import closure and scientific guardrails passed.')
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
printf '[Stage4.1R17 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.1R17 verify] complete unittest discovery passed.\n'
