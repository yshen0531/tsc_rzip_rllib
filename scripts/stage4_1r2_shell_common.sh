#!/usr/bin/env bash
# Shared helpers for the complete standalone Stage4.1R2 launchers.
# No Git, network access, or external source-tree recovery is used.

stage41r2_die() { echo "ERROR: $*" >&2; exit 2; }

stage41r2_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage41r2_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then PYTHON_BIN="$(command -v python)"
  else stage41r2_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage41r2_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage41r2_abspath() {
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

stage41r2_validate_source() {
  local run_dir="$1" relative
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage4_0_manifest.json"
    "stage4_0_state.json"
    "stage4_0_analysis/stage4_0_analysis_summary.json"
    "stage4_0_analysis/stage4_0_verdict.json"
  )
  for relative in "${required[@]}"; do [[ -f "${run_dir}/${relative}" ]] || return 1; done
  "${PYTHON_BIN}" - "${run_dir}" <<'PY' >/dev/null 2>&1
from pathlib import Path
import json,sys
run=Path(sys.argv[1])
manifest=json.loads((run/'stage4_0_manifest.json').read_text())
assert str(manifest.get('source_stage3_4_run','')).strip()
verdict=json.loads((run/'stage4_0_analysis/stage4_0_verdict.json').read_text())
assert verdict.get('stage') == 'Stage4.0'
PY
}

stage41r2_detect_source() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE4_0_RUN:-}" ]]; then
    candidate="$(stage41r2_abspath "${SOURCE_STAGE4_0_RUN}")"
    stage41r2_validate_source "${candidate}" || stage41r2_die "SOURCE_STAGE4_0_RUN is incomplete or unsupported: ${candidate}"
    SOURCE_STAGE4_0_RUN="${candidate}"; export SOURCE_STAGE4_0_RUN; return
  fi
  if [[ -f "${PROJECT_DIR}/stage4_0_runs/latest_stage4_0_run.txt" ]]; then
    candidate="$(head -n1 "${PROJECT_DIR}/stage4_0_runs/latest_stage4_0_run.txt" | tr -d '\r')"
    [[ -n "${candidate}" ]] && candidate="$(stage41r2_abspath "${candidate}")"
    if [[ -n "${candidate}" ]] && stage41r2_validate_source "${candidate}"; then
      SOURCE_STAGE4_0_RUN="${candidate}"; export SOURCE_STAGE4_0_RUN; return
    fi
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import json,sys
root=Path(sys.argv[1])/'stage4_0_runs'; items=[]
if root.is_dir():
  for p in root.glob('stage4_0_robustness_recovery_350ms_*'):
    req=(p/'stage4_0_manifest.json',p/'stage4_0_state.json',p/'stage4_0_analysis/stage4_0_analysis_summary.json',p/'stage4_0_analysis/stage4_0_verdict.json')
    if not (p.is_dir() and all(x.exists() for x in req)): continue
    try:
      state=json.loads((p/'stage4_0_state.json').read_text())
    except Exception: continue
    if state.get('finished') is True: items.append((p.stat().st_mtime,p.resolve()))
if items: print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage41r2_die "no complete Stage4.0 source found. Set SOURCE_STAGE4_0_RUN=/absolute/path/to/run"
  SOURCE_STAGE4_0_RUN="${candidate}"; export SOURCE_STAGE4_0_RUN
}

stage41r2_source_from_existing_run() {
  local run_dir="$1" candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json,sys
project=Path(sys.argv[1]).resolve(); run=Path(sys.argv[2]).resolve(); p=run/'stage4_1r2_manifest.json'
if not p.is_file(): raise SystemExit(0)
data=json.loads(p.read_text()); raw=str(data.get('source_stage4_0_run','')).strip()
if not raw: raise SystemExit(0)
path=Path(raw).expanduser()
if not path.exists():
  fallback=project/'stage4_0_runs'/path.name
  if fallback.exists(): path=fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE4_0_RUN:-}" && -n "${candidate}" ]]; then SOURCE_STAGE4_0_RUN="${candidate}"; export SOURCE_STAGE4_0_RUN; fi
}

stage41r2_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then command -v ray
  else printf '%s\n' ""; fi
}

stage41r2_ray_stop() {
  local ray_cli; ray_cli="$(stage41r2_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
 import ray; ray.shutdown()
except Exception: pass
PY
  fi
}

stage41r2_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != /tmp && "${value}" != /tmp/ ]] || stage41r2_die "${label} must be below /tmp; got ${value}"
}

stage41r2_cleanup_runtime() {
  local workspace="${STAGE4_1R2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE4_1R2_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage4_1r2_$(id -u)}"
  stage41r2_validate_tmp_path "${workspace}" STAGE4_1R2_TSC_WORKSPACE_ROOT
  stage41r2_validate_tmp_path "${run_root}" STAGE4_1R2_TSC_RUN_ROOT
  stage41r2_validate_tmp_path "${ray_tmp}" RAY_TMPDIR
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \( -name 'stage4_1r2*' -o -name 'stage41r2*' -o -name 'stage2_*' \) -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage41r2_runtime_env() {
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
  export VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 RAYON_NUM_THREADS=1 PYTHONUNBUFFERED=1
  export STAGE4_1R2_WORKERS="${STAGE4_1R2_WORKERS:-${STAGE4_WORKERS:-128}}"
  export STAGE4_WORKERS="${STAGE4_1R2_WORKERS}"
  export STAGE4_1_WORKERS="${STAGE4_1R2_WORKERS}"
  export STAGE2_WORKERS="${STAGE4_1R2_WORKERS}"
  export STAGE4_1R2_TSC_WORKSPACE_ROOT="${STAGE4_1R2_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE4_1R2_TSC_RUN_ROOT="${STAGE4_1R2_TSC_RUN_ROOT:-${STAGE4_1R2_TSC_WORKSPACE_ROOT}/episode_runs}"
  export STAGE4_1_TSC_WORKSPACE_ROOT="${STAGE4_1R2_TSC_WORKSPACE_ROOT}"
  export STAGE4_1_TSC_RUN_ROOT="${STAGE4_1R2_TSC_RUN_ROOT}"
  export STAGE3_4_TSC_WORKSPACE_ROOT="${STAGE4_1R2_TSC_WORKSPACE_ROOT}" STAGE3_4_TSC_RUN_ROOT="${STAGE4_1R2_TSC_RUN_ROOT}"
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE4_1R2_TSC_WORKSPACE_ROOT}" STAGE2_TSC_RUN_ROOT="${STAGE4_1R2_TSC_RUN_ROOT}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage4_1r2_$(id -u)}"
  export TMPDIR="${TMPDIR:-${RAY_TMPDIR}/tmp}"
  stage41r2_validate_tmp_path "${STAGE4_1R2_TSC_WORKSPACE_ROOT}" STAGE4_1R2_TSC_WORKSPACE_ROOT
  stage41r2_validate_tmp_path "${STAGE4_1R2_TSC_RUN_ROOT}" STAGE4_1R2_TSC_RUN_ROOT
  stage41r2_validate_tmp_path "${RAY_TMPDIR}" RAY_TMPDIR
  mkdir -p "${STAGE4_1R2_TSC_WORKSPACE_ROOT}" "${STAGE4_1R2_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true
  ulimit -u 262144 2>/dev/null || true
}
