#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_2R1_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"
for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json \
  configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json \
  configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json \
  scripts/stage4_2r1_true_tsc_plant_restart_action_replay.py \
  scripts/stage4_2r1_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_2r1_true_tsc_plant_restart_action_replay.py \
  tsc_rzip_rllib/diagnostics/stage4_1r17_original_deadline_one_sided_robust_braking_closure.py \
  tsc_rzip_rllib/core/runner.py \
  tests/test_stage4_2r1_true_tsc_plant_restart_action_replay.py \
  tests/test_ray_runtime_capacity.py \
  run_stage4_2r1_true_tsc_plant_restart_action_replay_native.sh \
  run_stage4_2r1_true_tsc_plant_restart_action_replay_nohup.sh \
  run_stage4_2r1_self_test.sh run_stage4_2r1_verify_package.sh \
  run_stop_stage4_2r1_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done
mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_2r1"* ]] || { echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2; exit 1; }
done
find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.2R1 verify] packaged file checksums passed.\n'
export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
expected = {
    'stage': 'Stage4.2R1',
    'controller_revision': 'true_tsc_plant_restart_action_replay_v42r1',
    'package_revision': 'r42r1a_capture_failure_finite_summary_v2',
    'run_name': 'stage4_2r1_true_tsc_plant_restart_action_replay',
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
    'stage4_1r17_runs', 'stage4_2r1_runs', 'logs', '__pycache__',
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

from tsc_rzip_rllib.diagnostics import stage4_2r1_true_tsc_plant_restart_action_replay as r42
from tsc_rzip_rllib.core.runner import TSCStepRunner

payload = r42.self_test()
if not payload.get('passed'):
    raise SystemExit('Stage4.2R1 self-test failed')
if not payload.get('incomparable_array_is_finite_json'):
    raise SystemExit('Stage4.2R1 finite-JSON mismatch guard failed')
if payload.get('checkpoint_step') != 20:
    raise SystemExit('Stage4.2R1 checkpoint changed')
if payload.get('expected_capture_rollouts') != 18 or payload.get('expected_restart_rollouts') != 18:
    raise SystemExit('Stage4.2R1 task matrix changed')
if payload.get('maximum_true_tsc_rollouts') != 36:
    raise SystemExit('Stage4.2R1 TSC budget changed')
if not payload.get('plant_restart_only') or payload.get('controller_checkpoint_replay_validated'):
    raise SystemExit('Stage4.2R1 plant/controller isolation changed')

cfg = json.loads(
    (root / 'configs/stage4_2r1_true_tsc_plant_restart_action_replay_370ms.json').read_text(encoding='utf-8')
)
r42.validate_config(cfg)
checkpoint = cfg['checkpoint']
contract = cfg['formal_timing_contract']
if checkpoint['checkpoint_step'] != 20 or checkpoint['checkpoint_elapsed_ms'] != 200:
    raise SystemExit('Stage4.2R1 capture checkpoint changed')
if checkpoint['normal_horizon_steps'] != 35 or checkpoint['weak_horizon_steps'] != 37:
    raise SystemExit('Stage4.2R1 formal horizon changed')
if contract['normal_slew']['arrival_deadline_step'] != 25 or contract['normal_slew']['hold_through_step'] != 35:
    raise SystemExit('normal 250/350 contract changed')
if contract['weak_slew']['arrival_deadline_step'] != 27 or contract['weak_slew']['hold_through_step'] != 37:
    raise SystemExit('weak 270/370 contract changed')
if contract['arrival_deadline_expansion_allowed']:
    raise SystemExit('arrival deadline expansion was enabled')
if checkpoint['controller_checkpoint_replay_in_this_stage']:
    raise SystemExit('controller checkpoint replay leaked into plant restart R1')
if not cfg['stage4_2r1_old_r11_based_package_was_not_run_or_reused']:
    raise SystemExit('old unrun R11-based R1 package reuse guard disabled')
if cfg['source_requirements']['required_package_revision'] != 'r17a_output_vector_contract_hotfix_v2':
    raise SystemExit('R17a source package contract changed')
if cfg['matrix']['expected_source_cases'] != 18 or cfg['matrix']['expected_capture_rollouts'] != 18 or cfg['matrix']['expected_restart_rollouts'] != 18:
    raise SystemExit('Stage4.2R1 finite matrix changed')

module = (
    root / 'tsc_rzip_rllib/diagnostics/stage4_2r1_true_tsc_plant_restart_action_replay.py'
).read_text(encoding='utf-8')
for token in (
    'request_restart_snapshot',
    'restart_snapshot_manifest.json',
    'wire_currents_a',
    'snapshot_wire_vector_exact_to_capture_state',
    'fresh_restart_actor',
    'controller_checkpoint_loaded": False',
    'plant_restart_fidelity_pass',
    'formal_contract_pass',
    'old_unrun_r11_based_stage4_2r1_not_reused',
    'capture_exception_stage',
    '_finite_metric_max',
    'capture_visible_comparable_fraction',
):
    if token not in module:
        raise SystemExit(f'Stage4.2R1 implementation guard missing: {token}')
for method in ('request_restart_snapshot', 'clear_restart_snapshot_requests', 'export_restart_snapshot'):
    if not hasattr(TSCStepRunner, method):
        raise SystemExit(f'TSCStepRunner snapshot API missing: {method}')
native_source = (root / 'run_stage4_2r1_true_tsc_plant_restart_action_replay_native.sh').read_text(encoding='utf-8')
if 'R10/R11 750 ms/2 s trajectories remain auxiliary' not in native_source:
    raise SystemExit('long-horizon auxiliary-only runtime warning missing')
runner_source = (root / 'tsc_rzip_rllib/core/runner.py').read_text(encoding='utf-8')
for token in ('_restart_snapshot_requests', 'self.export_restart_snapshot(requested)', 'sprsina', 'wire_currents.csv'):
    if token not in runner_source:
        raise SystemExit(f'runner snapshot guard missing: {token}')
print('[Stage4.2R1 verify] Python compile, JSON parse, internal import closure and scientific guardrails passed.')
PY
mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
printf '[Stage4.2R1 verify] declared shell scripts passed bash -n.\n'
"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.2R1 verify] complete unittest discovery passed.\n'
