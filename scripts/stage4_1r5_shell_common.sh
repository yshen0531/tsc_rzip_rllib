#!/usr/bin/env bash
# Shared helpers for the complete standalone Stage4.1R5 launchers.
# No Git, network access, or external source-tree recovery is used.

stage41r5_die() { echo "ERROR: $*" >&2; exit 2; }

stage41r5_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage41r5_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    stage41r5_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage41r5_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage41r5_abspath() {
  local value="${1:-}"
  [[ -n "${value}" ]] || return 1
  "${PYTHON_BIN}" - "${PROJECT_DIR}" "${value}" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); value=Path(sys.argv[2]).expanduser()
if not value.is_absolute(): value=root/value
print(value.resolve(strict=False))
PY
}

stage41r5_validate_source() {
  local run_dir="$1" relative
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage4_1r4_manifest.json"
    "stage4_1r4_state.json"
    "stage4_1r4_config.resolved.json"
    "stage4_1r4_analysis/stage4_1r4_verdict.json"
    "stage4_1r4_weak_slew_370ms/summary.json"
    "stage4_1r4_delay_slew_estimator/summary.json"
  )
  for relative in "${required[@]}"; do [[ -f "${run_dir}/${relative}" ]] || return 1; done
  "${PYTHON_BIN}" - "${run_dir}" <<'PYI' >/dev/null 2>&1
from pathlib import Path
import json,sys
run=Path(sys.argv[1])
manifest=json.loads((run/'stage4_1r4_manifest.json').read_text())
state=json.loads((run/'stage4_1r4_state.json').read_text())
assert manifest.get('stage') == 'Stage4.1R4'
assert manifest.get('controller_revision') == 'targeted_weak_slew_and_online_delay_slew_estimator_v4'
assert state.get('finished') is True
reclass=state.get('reclassification_summary') or {}
weak=state.get('weak_slew_summary') or {}
est=state.get('estimator_summary') or {}
assert reclass.get('gain_estimation_error_reclassified_without_new_tsc') is True
assert reclass.get('all_non_slew_required_categories_passed') is True
assert weak.get('passed') is True
assert est.get('estimator_accuracy_passed') is True
# The source adaptive controller is expected to be incomplete; R5 closes handover.
PYI
}

stage41r5_detect_source() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE4_1R4_RUN:-}" ]]; then
    candidate="$(stage41r5_abspath "${SOURCE_STAGE4_1R4_RUN}")"
    stage41r5_validate_source "${candidate}" || stage41r5_die "SOURCE_STAGE4_1R4_RUN is incomplete or unsupported: ${candidate}"
    SOURCE_STAGE4_1R4_RUN="${candidate}"; export SOURCE_STAGE4_1R4_RUN; return
  fi
  if [[ -f "${PROJECT_DIR}/stage4_1r4_runs/latest_stage4_1r4_run.txt" ]]; then
    candidate="$(head -n1 "${PROJECT_DIR}/stage4_1r4_runs/latest_stage4_1r4_run.txt" | tr -d '\r')"
    [[ -n "${candidate}" ]] && candidate="$(stage41r5_abspath "${candidate}")"
    if [[ -n "${candidate}" ]] && stage41r5_validate_source "${candidate}"; then
      SOURCE_STAGE4_1R4_RUN="${candidate}"; export SOURCE_STAGE4_1R4_RUN; return
    fi
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PYI'
from pathlib import Path
import json,sys
root=Path(sys.argv[1])/'stage4_1r4_runs'; items=[]
if root.is_dir():
  for p in root.glob('stage4_1r4_targeted_closure_370ms_*'):
    req=(p/'stage4_1r4_manifest.json',p/'stage4_1r4_state.json',p/'stage4_1r4_analysis/stage4_1r4_verdict.json')
    if not (p.is_dir() and all(x.exists() for x in req)): continue
    try:
      manifest=json.loads((p/'stage4_1r4_manifest.json').read_text())
      state=json.loads((p/'stage4_1r4_state.json').read_text())
    except Exception: continue
    if (manifest.get('stage')=='Stage4.1R4' and
        manifest.get('controller_revision')=='targeted_weak_slew_and_online_delay_slew_estimator_v4' and
        state.get('finished') is True and
        (state.get('weak_slew_summary') or {}).get('passed') is True and
        (state.get('estimator_summary') or {}).get('estimator_accuracy_passed') is True):
      items.append((p.stat().st_mtime,p.resolve()))
if items: print(max(items)[1])
PYI
)"
  [[ -n "${candidate}" ]] || stage41r5_die "no complete Stage4.1R4 source found. Set SOURCE_STAGE4_1R4_RUN=/absolute/path/to/run"
  SOURCE_STAGE4_1R4_RUN="${candidate}"; export SOURCE_STAGE4_1R4_RUN
}

stage41r5_source_from_existing_run() {
  local run_dir="$1" candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]).resolve(); run=Path(sys.argv[2]).resolve(); p=run/'stage4_1r5_manifest.json'
if not p.is_file(): raise SystemExit(0)
data=json.loads(p.read_text()); raw=str(data.get('source_stage4_1r4_run','')).strip()
if not raw: raise SystemExit(0)
path=Path(raw).expanduser()
if not path.exists():
  fallback=project/'stage4_1r4_runs'/path.name
  if fallback.exists(): path=fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE4_1R4_RUN:-}" && -n "${candidate}" ]]; then
    SOURCE_STAGE4_1R4_RUN="${candidate}"; export SOURCE_STAGE4_1R4_RUN
  fi
}

stage41r5_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then command -v ray
  else printf '%s\n' ""; fi
}

stage41r5_ray_stop() {
  local ray_cli; ray_cli="$(stage41r5_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then
    "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else
    "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
 import ray; ray.shutdown()
except Exception: pass
PY
  fi
}

stage41r5_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != /tmp && "${value}" != /tmp/ ]] || \
    stage41r5_die "${label} must be below /tmp; got ${value}"
}

stage41r5_cleanup_runtime() {
  local workspace="${STAGE4_1R5_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE4_1R5_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage4_1r5_$(id -u)}"
  stage41r5_validate_tmp_path "${workspace}" STAGE4_1R5_TSC_WORKSPACE_ROOT
  stage41r5_validate_tmp_path "${run_root}" STAGE4_1R5_TSC_RUN_ROOT
  stage41r5_validate_tmp_path "${ray_tmp}" RAY_TMPDIR
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \
    \( -name 'stage4_1r5*' -o -name 'stage41r5*' -o -name 'stage2_*' \) \
    -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage41r5_runtime_env() {
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
  export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1 PYTHONUNBUFFERED=1
  export STAGE4_1R5_WORKERS="${STAGE4_1R5_WORKERS:-${STAGE4_WORKERS:-128}}"
  export STAGE4_WORKERS="${STAGE4_1R5_WORKERS}"
  export STAGE4_1_WORKERS="${STAGE4_1R5_WORKERS}"
  export STAGE2_WORKERS="${STAGE4_1R5_WORKERS}"
  export STAGE4_1R5_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE4_1R5_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT:-${STAGE4_1R5_TSC_WORKSPACE_ROOT}/episode_runs}"
  export STAGE4_1R4_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R4_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT}"
  export STAGE4_1R3_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT}"
  export STAGE4_1R3_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT}"
  export STAGE4_1_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT}"
  export STAGE4_1_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT}"
  export STAGE3_4_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT}"
  export STAGE3_4_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT}"
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE4_1R5_TSC_WORKSPACE_ROOT}"
  export STAGE2_TSC_RUN_ROOT="${STAGE4_1R5_TSC_RUN_ROOT}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r5_$(id -u)}"
  export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"
  stage41r5_validate_tmp_path "${STAGE4_1R5_TSC_WORKSPACE_ROOT}" STAGE4_1R5_TSC_WORKSPACE_ROOT
  stage41r5_validate_tmp_path "${STAGE4_1R5_TSC_RUN_ROOT}" STAGE4_1R5_TSC_RUN_ROOT
  stage41r5_validate_tmp_path "${RAY_TMPDIR}" RAY_TMPDIR
  mkdir -p "${STAGE4_1R5_TSC_WORKSPACE_ROOT}" "${STAGE4_1R5_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true
  ulimit -u 262144 2>/dev/null || true
}
