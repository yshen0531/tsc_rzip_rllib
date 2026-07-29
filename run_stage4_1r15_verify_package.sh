#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${STAGE4_1R15_PYTHON:-${PYTHON:-python3}}"
cd "${PROJECT_DIR}"

for path in \
  PACKAGE_MANIFEST.json SHA256SUMS \
  configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json \
  scripts/stage4_1r15_bounded_early_braking_local_response_identification.py \
  scripts/stage4_1r15_shell_common.sh \
  tsc_rzip_rllib/diagnostics/stage4_1r15_bounded_early_braking_local_response_identification.py \
  tsc_rzip_rllib/diagnostics/stage4_1r14_original_deadline_integrated_target_conditioned_deadline_mpc.py \
  tests/test_stage4_1r15_bounded_early_braking_local_response_identification.py \
  tests/test_ray_runtime_capacity.py \
  run_stage4_1r15_bounded_early_braking_local_response_identification_native.sh \
  run_stage4_1r15_bounded_early_braking_local_response_identification_nohup.sh \
  run_stage4_1r15_self_test.sh run_stage4_1r15_verify_package.sh run_stop_stage4_1r15_now.sh; do
  [[ -f "${path}" ]] || { echo "ERROR: required packaged file missing: ${path}" >&2; exit 1; }
done

mapfile -t ROOT_STAGE_SH < <(find . -maxdepth 1 -type f -name 'run_stage*.sh' -printf '%f\n' | sort)
for script in "${ROOT_STAGE_SH[@]}"; do
  [[ "${script}" == *"stage4_1r15"* ]] || { echo "ERROR: obsolete root-stage shell script is packaged: ${script}" >&2; exit 1; }
done

find configs scripts tests tsc_rzip_rllib -type d -name '__pycache__' -prune -exec rm -rf {} +
find configs scripts tests tsc_rzip_rllib -type f -name '*.pyc' -delete
sha256sum -c SHA256SUMS
printf '[Stage4.1R15 verify] packaged file checksums passed.\n'

export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations
import ast, json
from pathlib import Path

root=Path.cwd()
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text())
expected={
 'stage':'Stage4.1R15',
 'controller_revision':'bounded_early_braking_local_response_identification_v15',
 'package_revision':'r15_bounded_local_response_identification_v1',
 'run_name':'stage4_1r15_bounded_early_braking_local_response_identification',
}
for k,v in expected.items():
    if manifest.get(k)!=v: raise SystemExit(f'PACKAGE_MANIFEST {k} mismatch: {manifest.get(k)!r} != {v!r}')
rows=[x for x in (root/'SHA256SUMS').read_text().splitlines() if x.strip()]
listed=[x.split(None,1)[1].strip() for x in rows]
if len(rows)!=manifest.get('declared_file_count'): raise SystemExit('declared file count mismatch')
if listed!=manifest.get('file_inventory'): raise SystemExit('manifest inventory differs from SHA256SUMS')
if listed!=sorted(set(listed)): raise SystemExit('inventory must be sorted and unique')
if 'PACKAGE_MANIFEST.json' not in listed or 'SHA256SUMS' in listed: raise SystemExit('checksum self/inventory guard failed')

actual=[]
for directory in ('configs','scripts','tests','tsc_rzip_rllib'):
    for p in sorted((root/directory).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc': actual.append(str(p.relative_to(root)))
listed_replaced=[x for x in listed if x.split('/',1)[0] in {'configs','scripts','tests','tsc_rzip_rllib'}]
if actual!=listed_replaced: raise SystemExit(f'replaced-tree inventory mismatch missing={sorted(set(actual)-set(listed_replaced))[:10]} extra={sorted(set(listed_replaced)-set(actual))[:10]}')

ignored={'stage2_runs','stage3_runs','stage3_4_runs','stage4_runs','stage4_1r6_runs','stage4_1r7_runs','stage4_1r8_runs','stage4_1r9_runs','stage4_1r10_runs','stage4_1r11_runs','stage4_1r12_runs','stage4_1r13_runs','stage4_1r14_runs','stage4_1r15_runs','logs','__pycache__'}
for p in sorted(root.rglob('*.py')):
    if any(part in ignored for part in p.parts): continue
    src=p.read_text(encoding='utf-8'); compile(src,str(p),'exec'); ast.parse(src,filename=str(p))
for p in sorted((root/'configs').glob('*.json')): json.loads(p.read_text())

modules=set(); module_by_path={}
for p in sorted((root/'tsc_rzip_rllib').rglob('*.py')):
    module='.'.join(p.parent.relative_to(root).parts) if p.name=='__init__.py' else '.'.join(p.relative_to(root).with_suffix('').parts)
    modules.add(module); module_by_path[p]=module

def resolve(pkg, level, module):
    if level==0: return module or ''
    parts=pkg.split('.') if pkg else []; drop=level-1
    if drop>len(parts): raise SystemExit(f'invalid relative import {pkg} level={level}')
    parts=parts[:len(parts)-drop]
    if module: parts.extend(module.split('.'))
    return '.'.join(parts)
missing=[]
for p,mod in module_by_path.items():
    pkg=mod if p.name=='__init__.py' else mod.rsplit('.',1)[0]
    tree=ast.parse(p.read_text(),filename=str(p))
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for a in node.names:
                n=a.name
                if n.startswith('tsc_rzip_rllib') and not any(n==m or n.startswith(m+'.') for m in modules): missing.append((str(p),n))
        elif isinstance(node,ast.ImportFrom):
            base=resolve(pkg,node.level,node.module)
            if base.startswith('tsc_rzip_rllib') and base not in modules and not any(m.startswith(base+'.') for m in modules): missing.append((str(p),base))
if missing: raise SystemExit('missing packaged internal imports: '+repr(missing[:20]))

from tsc_rzip_rllib.diagnostics import stage4_1r15_bounded_early_braking_local_response_identification as r15
payload=r15.self_test(root)
if not payload.get('passed'): raise SystemExit('R15 self-test failed')
if payload.get('expected_true_tsc_probe_rollouts')!=32: raise SystemExit('R15 probe budget changed')
if payload.get('probe_schedule_variants_per_target')!=16: raise SystemExit('R15 probe schedule count changed')
if not payload.get('all_probes_zero_net'): raise SystemExit('R15 zero-net guard failed')
if payload.get('formal_timing_contract_restored_by_this_stage'): raise SystemExit('R15 may not claim formal closure')
if not payload.get('stage4_2r1_was_not_run_or_reused'): raise SystemExit('R15 must not reuse Stage4.2R1')

cfg=json.loads((root/'configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json').read_text())
r15.validate_config(cfg)
if cfg['formal_timing_contract']['normal_slew']['arrival_deadline_step']!=25 or cfg['formal_timing_contract']['weak_slew']['arrival_deadline_step']!=27: raise SystemExit('formal timing changed')
if cfg['local_response_model']['output_state_end_inclusive']!=37: raise SystemExit('local model does not cover formal hold state37')
if cfg['bounded_probe_validation']['expected_rollouts']!=32: raise SystemExit('probe count changed')
if cfg['bounded_probe_validation']['formal_tracking_pass_is_not_required_for_identification_probes'] is not True: raise SystemExit('identification/tracking semantics changed')
if cfg['formal_timing_contract_restored_by_this_stage'] is not False: raise SystemExit('identification stage claims closure')
if cfg['stage4_2r1_was_not_run_or_reused'] is not True: raise SystemExit('Stage4.2R1 guard disabled')

module=(root/'tsc_rzip_rllib/diagnostics/stage4_1r15_bounded_early_braking_local_response_identification.py').read_text()
for token in ('applied_probe_zero_net','nonzero_feedforward_rows_beyond_state35' if False else 'beyond_horizon_feedforward_row_count','formal_tracking_pass_required'):
    if token not in module: raise SystemExit(f'R15 implementation guard missing: {token}')
print('[Stage4.1R15 verify] Python compile, JSON parse, internal import closure and scientific guardrails passed.')
PY

mapfile -t SHELLS < <(find . -maxdepth 2 -type f -name '*.sh' -print | sort)
for script in "${SHELLS[@]}"; do bash -n "${script}"; done
printf '[Stage4.1R15 verify] declared shell scripts passed bash -n.\n'

"${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'
printf '[Stage4.1R15 verify] complete unittest discovery passed.\n'
