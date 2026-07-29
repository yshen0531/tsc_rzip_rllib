#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R16_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"
for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json \
  configs/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation_370ms.json \
  configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json \
  scripts/stage4_1r16_amplitude_certified_probe_derived_braking_closure.py \
  scripts/stage4_1r16_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r16_amplitude_certified_probe_derived_braking_closure.py \
  tsc_rzip_rllib/diagnostics/stage4_1r15b_probe_derived_symmetric_local_response_superposition_validation.py \
  tsc_rzip_rllib/diagnostics/stage4_1r15_bounded_early_braking_local_response_identification.py \
  tests/test_stage4_1r16_amplitude_certified_probe_derived_braking_closure.py \
  tests/test_ray_runtime_capacity.py \
  run_stage4_1r16_amplitude_certified_probe_derived_braking_closure_native.sh \
  run_stage4_1r16_amplitude_certified_probe_derived_braking_closure_nohup.sh \
  run_stage4_1r16_self_test.sh run_stage4_1r16_verify_package.sh \
  run_stop_stage4_1r16_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r16"* ]] || { echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2; exit 1; }
done
find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.1R16 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
expected = {
    'stage': 'Stage4.1R16',
    'controller_revision': 'amplitude_certified_probe_derived_braking_closure_v16',
    'package_revision': 'r16_joint_envelope_amplitude_ladder_formal_closure_v1',
    'run_name': 'stage4_1r16_amplitude_certified_probe_derived_braking_closure',
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
    'logs', '__pycache__',
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

from tsc_rzip_rllib.diagnostics import stage4_1r16_amplitude_certified_probe_derived_braking_closure as r16

payload = r16.self_test(root)
if not payload.get('passed'):
    raise SystemExit('R16 self-test failed')
if payload.get('expected_true_tsc_amplitude_rollouts') != 32:
    raise SystemExit('R16 amplitude rollout budget changed')
if payload.get('expected_true_tsc_calibrated_rollouts') != 4:
    raise SystemExit('R16 calibrated rollout budget changed')
if payload.get('maximum_true_tsc_rollouts') != 36:
    raise SystemExit('R16 maximum rollout budget changed')
if not payload.get('all_schedules_zero_net'):
    raise SystemExit('R16 zero-net schedule guard failed')
if abs(float(payload.get('maximum_schedule_component')) - 0.09) > 1e-12:
    raise SystemExit('R16 maximum schedule component changed')

cfg = json.loads(
    (root / 'configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json').read_text(encoding='utf-8')
)
r16.validate_config(cfg)
if cfg['formal_timing_contract']['normal_slew']['arrival_deadline_step'] != 25:
    raise SystemExit('normal arrival deadline changed')
if cfg['formal_timing_contract']['weak_slew']['arrival_deadline_step'] != 27:
    raise SystemExit('weak arrival deadline changed')
amp = cfg['amplitude_envelope_validation']
if amp['magnitude_levels'] != [1.0, 2.0, 4.0, 6.0]:
    raise SystemExit('R16 amplitude ladder changed')
if amp['closure_candidate_magnitude'] != 6.0 or amp['braking_sign'] != -1:
    raise SystemExit('R16 preregistered candidate changed')
if amp['expected_rollouts'] != 32 or cfg['calibrated_confirmation']['expected_rollouts'] != 4:
    raise SystemExit('R16 task matrix changed')
if not cfg['finite_test_envelope_only'] or cfg['unseen_target_generalization_validated']:
    raise SystemExit('R16 finite-envelope semantics changed')
if not cfg['stage4_2r1_was_not_run_or_reused']:
    raise SystemExit('R16 may not reuse Stage4.2R1')
module = (
    root / 'tsc_rzip_rllib/diagnostics/stage4_1r16_amplitude_certified_probe_derived_braking_closure.py'
).read_text(encoding='utf-8')
for token in (
    'source_joint_h0_coverage_exact',
    'candidate_was_preregistered_from_source_model_not_selected_from_new_tsc',
    'maximum_per_unit_velocity_response_rmse_m_per_s',
    'closure_candidate_minimum_signed_margin',
    'formal_grid_confirmation',
    'stage4_2r1_was_not_run_or_reused',
):
    if token not in module:
        raise SystemExit(f'R16 implementation guard missing: {token}')
print('[Stage4.1R16 verify] Python compile, JSON parse, internal import closure and scientific guardrails passed.')
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
printf '[Stage4.1R16 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.1R16 verify] complete unittest discovery passed.\n'
