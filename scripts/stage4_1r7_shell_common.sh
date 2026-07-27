#!/usr/bin/env bash
# Shared helpers for the complete standalone Stage4.1R7 launchers.
# No Git, network access, or external source-tree recovery is used.

stage41r7_die() { echo "ERROR: $*" >&2; exit 2; }

stage41r7_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage41r7_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    stage41r7_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage41r7_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage41r7_abspath() {
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

stage41r7_validate_source() {
  local run_dir="$1" relative
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage4_1r6_manifest.json"
    "stage4_1r6_state.json"
    "stage4_1r6_config.resolved.json"
    "stage4_1r6_analysis/stage4_1r6_verdict.json"
    "stage4_1r6_estimator_confirmation/summary.json"
    "stage4_1r6_static_startup/summary.json"
  )
  for relative in "${required[@]}"; do [[ -f "${run_dir}/${relative}" ]] || return 1; done
  "${PYTHON_BIN}" - "${run_dir}" <<'PYI' >/dev/null 2>&1
from pathlib import Path
import json,sys
run=Path(sys.argv[1])
manifest=json.loads((run/'stage4_1r6_manifest.json').read_text())
state=json.loads((run/'stage4_1r6_state.json').read_text())
assert manifest.get('stage') == 'Stage4.1R6'
assert manifest.get('controller_revision') == 'confidence_gated_persistent_prior_physical_handover_v6'
assert state.get('finished') is True
source=state.get('source_audit_summary') or {}
est=state.get('estimator_confirmation_summary') or {}
static=state.get('startup_summary') or {}
assert source.get('passed') is True
assert est.get('passed') is True
assert abs(float(static.get('persistent_exact_preservation_fraction',0.0))-1.0) <= 1e-12
assert abs(float(static.get('persistent_exact_trace_equivalence_fraction',0.0))-1.0) <= 1e-12
# The source adjacent/cold startup paths are expected to be incomplete.
PYI
}

stage41r7_detect_source() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE4_1R6_RUN:-}" ]]; then
    candidate="$(stage41r7_abspath "${SOURCE_STAGE4_1R6_RUN}")"
    stage41r7_validate_source "${candidate}" || stage41r7_die "SOURCE_STAGE4_1R6_RUN is incomplete or unsupported: ${candidate}"
    SOURCE_STAGE4_1R6_RUN="${candidate}"; export SOURCE_STAGE4_1R6_RUN
    return
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PYI'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]); items=[]
for p in (project/'stage4_1r6_runs').glob('stage4_1r6_startup_architecture_closure_350ms_*'):
  try:
    m=json.loads((p/'stage4_1r6_manifest.json').read_text())
    s=json.loads((p/'stage4_1r6_state.json').read_text())
  except Exception: continue
  if (m.get('stage')=='Stage4.1R6' and
      m.get('controller_revision')=='confidence_gated_persistent_prior_physical_handover_v6' and
      s.get('finished') is True and
      (s.get('source_audit_summary') or {}).get('passed') is True and
      (s.get('estimator_confirmation_summary') or {}).get('passed') is True and
      abs(float((s.get('startup_summary') or {}).get('persistent_exact_preservation_fraction',0.0))-1.0)<=1e-12):
    items.append((p.stat().st_mtime,p.resolve()))
if items: print(max(items)[1])
PYI
)"
  [[ -n "${candidate}" ]] || stage41r7_die "no complete Stage4.1R6 source found. Set SOURCE_STAGE4_1R6_RUN=/absolute/path/to/run"
  SOURCE_STAGE4_1R6_RUN="${candidate}"; export SOURCE_STAGE4_1R6_RUN
}

stage41r7_source_from_existing_run() {
  local run_dir="$1" candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]).resolve(); run=Path(sys.argv[2]).resolve(); p=run/'stage4_1r7_manifest.json'
if not p.is_file(): raise SystemExit(0)
data=json.loads(p.read_text()); raw=str(data.get('source_stage4_1r6_run','')).strip()
if not raw: raise SystemExit(0)
path=Path(raw).expanduser()
if not path.exists():
  fallback=project/'stage4_1r6_runs'/path.name
  if fallback.exists(): path=fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE4_1R6_RUN:-}" && -n "${candidate}" ]]; then
    SOURCE_STAGE4_1R6_RUN="${candidate}"; export SOURCE_STAGE4_1R6_RUN
  fi
}

stage41r7_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then command -v ray
  else printf '%s\n' ""; fi
}

stage41r7_ray_stop() {
  local ray_cli; ray_cli="$(stage41r7_find_ray_cli)"
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

stage41r7_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != /tmp && "${value}" != /tmp/ ]] || \
    stage41r7_die "${label} must be below /tmp; got ${value}"
}

stage41r7_cleanup_runtime() {
  local workspace="${STAGE4_1R7_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE4_1R7_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage4_1r7_$(id -u)}"
  stage41r7_validate_tmp_path "${workspace}" STAGE4_1R7_TSC_WORKSPACE_ROOT
  stage41r7_validate_tmp_path "${run_root}" STAGE4_1R7_TSC_RUN_ROOT
  stage41r7_validate_tmp_path "${ray_tmp}" RAY_TMPDIR
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \
    \( -name 'stage4_1r7*' -o -name 'stage41r7*' -o -name 'stage2_*' \) \
    -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage41r7_runtime_env() {
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
  export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1 PYTHONUNBUFFERED=1
  export STAGE4_1R7_WORKERS="${STAGE4_1R7_WORKERS:-${STAGE4_WORKERS:-128}}"
  export STAGE4_WORKERS="${STAGE4_1R7_WORKERS}"
  export STAGE4_1_WORKERS="${STAGE4_1R7_WORKERS}"
  export STAGE2_WORKERS="${STAGE4_1R7_WORKERS}"
  export STAGE4_1R7_TSC_WORKSPACE_ROOT="${STAGE4_1R7_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE4_1R7_TSC_RUN_ROOT="${STAGE4_1R7_TSC_RUN_ROOT:-${STAGE4_1R7_TSC_WORKSPACE_ROOT}/episode_runs}"
  for prefix in STAGE4_1R6 STAGE4_1R5 STAGE4_1R4 STAGE4_1R3 STAGE4_1 STAGE3_4 STAGE2; do
    export "${prefix}_TSC_WORKSPACE_ROOT=${STAGE4_1R7_TSC_WORKSPACE_ROOT}"
    export "${prefix}_TSC_RUN_ROOT=${STAGE4_1R7_TSC_RUN_ROOT}"
  done
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r7_$(id -u)}"
  export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"
  stage41r7_validate_tmp_path "${STAGE4_1R7_TSC_WORKSPACE_ROOT}" STAGE4_1R7_TSC_WORKSPACE_ROOT
  stage41r7_validate_tmp_path "${STAGE4_1R7_TSC_RUN_ROOT}" STAGE4_1R7_TSC_RUN_ROOT
  stage41r7_validate_tmp_path "${RAY_TMPDIR}" RAY_TMPDIR
  mkdir -p "${STAGE4_1R7_TSC_WORKSPACE_ROOT}" "${STAGE4_1R7_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true
  ulimit -u 262144 2>/dev/null || true
}
