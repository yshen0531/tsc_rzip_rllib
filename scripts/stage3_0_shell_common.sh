#!/usr/bin/env bash
# Shared helpers for the standalone Stage3.0 launchers.
# Local path discovery only: no Git, network, or external source-tree recovery.

stage30_die() {
  echo "ERROR: $*" >&2
  exit 2
}

stage30_project_init() {
  local caller_dir
  caller_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
  export PROJECT_DIR="${PROJECT_DIR:-${caller_dir}}"
  PROJECT_DIR="$(cd "${PROJECT_DIR}" && pwd)"
  export PROJECT_DIR
  export TSC_ALL_ROOT="${TSC_ALL_ROOT:-$(cd "${PROJECT_DIR}/.." && pwd)}"
  export PYTHONPATH="${PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
  cd "${PROJECT_DIR}"
}

stage30_find_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    :
  elif [[ -x "${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python" ]]; then
    PYTHON_BIN="${TSC_ALL_ROOT}/tsc_simulation/venv_simu/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  else
    stage30_die "no Python interpreter found; set PYTHON_BIN=/absolute/path/to/python"
  fi
  [[ -x "${PYTHON_BIN}" ]] || stage30_die "Python interpreter is not executable: ${PYTHON_BIN}"
  export PYTHON_BIN
}

stage30_abspath() {
  local value="${1:-}"
  [[ -n "${value}" ]] || return 1
  "${PYTHON_BIN}" - "${PROJECT_DIR}" "${value}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]).expanduser().resolve()
value = Path(sys.argv[2]).expanduser()
if not value.is_absolute():
    value = root / value
print(value.resolve(strict=False))
PY
}

stage30_validate_stage22_source() {
  local run_dir="$1"
  [[ -d "${run_dir}" ]] || return 1
  local required=(
    "stage2_2_config.resolved.json"
    "stage2_2_manifest.json"
    "stage2_2_analysis/all_generation_results.json"
    "stage2_2_analysis/corner_hall_of_fame.json"
    "stage2_2_analysis/speed_safe_hall_of_fame.json"
    "stage2_2_analysis/gate_hall_of_fame.json"
    "env_config.resolved.json"
    "train_config.resolved.json"
    "source_reference/analysis/coil_modes_tsc.npy"
  )
  local relative
  for relative in "${required[@]}"; do
    [[ -f "${run_dir}/${relative}" ]] || return 1
  done
  [[ -d "${run_dir}/stage2_2_evaluations" ]] || return 1
}

stage30_detect_source_stage22() {
  local candidate=""
  if [[ -n "${SOURCE_STAGE2_2_RUN:-}" ]]; then
    candidate="$(stage30_abspath "${SOURCE_STAGE2_2_RUN}")"
    stage30_validate_stage22_source "${candidate}" || \
      stage30_die "SOURCE_STAGE2_2_RUN is not a complete Stage2.2 run: ${candidate}"
    SOURCE_STAGE2_2_RUN="${candidate}"
    export SOURCE_STAGE2_2_RUN
    return
  fi
  if [[ -f "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt" ]]; then
    candidate="$(head -n 1 "${PROJECT_DIR}/stage2_2_runs/latest_stage2_2_run.txt" | tr -d '\r')"
    if [[ -n "${candidate}" ]]; then
      candidate="$(stage30_abspath "${candidate}")"
      if stage30_validate_stage22_source "${candidate}"; then
        SOURCE_STAGE2_2_RUN="${candidate}"
        export SOURCE_STAGE2_2_RUN
        return
      fi
    fi
  fi
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1]) / "stage2_2_runs"
items = []
if root.is_dir():
    for path in root.glob("stage2_2_svd3_corner_feasibility_100ms_*"):
        required = (
            path / "stage2_2_config.resolved.json",
            path / "stage2_2_manifest.json",
            path / "stage2_2_analysis/all_generation_results.json",
            path / "stage2_2_analysis/corner_hall_of_fame.json",
            path / "stage2_2_analysis/speed_safe_hall_of_fame.json",
            path / "stage2_2_analysis/gate_hall_of_fame.json",
            path / "env_config.resolved.json",
            path / "train_config.resolved.json",
            path / "source_reference/analysis/coil_modes_tsc.npy",
            path / "stage2_2_evaluations",
        )
        if path.is_dir() and all(item.exists() for item in required):
            items.append((path.stat().st_mtime, path.resolve()))
if items:
    print(max(items)[1])
PY
)"
  [[ -n "${candidate}" ]] || stage30_die \
    "no complete Stage2.2 source run found. Set SOURCE_STAGE2_2_RUN=/absolute/path/to/stage2_2_run"
  SOURCE_STAGE2_2_RUN="${candidate}"
  export SOURCE_STAGE2_2_RUN
}

stage30_source_from_existing_run() {
  local run_dir="$1"
  local candidate
  candidate="$("${PYTHON_BIN}" - "${PROJECT_DIR}" "${run_dir}" <<'PY'
from pathlib import Path
import json, sys
project = Path(sys.argv[1]).resolve()
run = Path(sys.argv[2]).resolve()
manifest = run / "stage3_0_manifest.json"
if not manifest.is_file():
    raise SystemExit(0)
data = json.loads(manifest.read_text(encoding="utf-8"))
raw = str(data.get("source_stage2_2_run", "")).strip()
if not raw:
    raise SystemExit(0)
path = Path(raw).expanduser()
if not path.is_absolute():
    path = project / path
if not path.exists():
    fallback = project / "stage2_2_runs" / Path(raw).name
    if fallback.exists():
        path = fallback
print(path.resolve(strict=False))
PY
)"
  if [[ -z "${SOURCE_STAGE2_2_RUN:-}" && -n "${candidate}" ]]; then
    SOURCE_STAGE2_2_RUN="${candidate}"
    export SOURCE_STAGE2_2_RUN
  fi
}

stage30_resolve_existing_run() {
  local value="${STAGE3_0_RUN_DIR:-}"
  if [[ -z "${value}" && -f "${PROJECT_DIR}/stage3_0_runs/latest_stage3_0_run.txt" ]]; then
    value="$(head -n 1 "${PROJECT_DIR}/stage3_0_runs/latest_stage3_0_run.txt" | tr -d '\r')"
  fi
  [[ -n "${value}" ]] || stage30_die "no Stage3.0 run selected. Set STAGE3_0_RUN_DIR or create a run first"
  value="$(stage30_abspath "${value}")"
  [[ -d "${value}" ]] || stage30_die "Stage3.0 run directory does not exist: ${value}"
  [[ -f "${value}/stage3_0_manifest.json" ]] || stage30_die "not a prepared Stage3.0 run: ${value}"
  STAGE3_0_RUN_DIR="${value}"
  export STAGE3_0_RUN_DIR
}

stage30_find_ray_cli() {
  local candidate="$(dirname "${PYTHON_BIN}")/ray"
  if [[ -x "${candidate}" ]]; then
    printf '%s\n' "${candidate}"
  elif command -v ray >/dev/null 2>&1; then
    command -v ray
  else
    printf '%s\n' ""
  fi
}

stage30_ray_stop() {
  local ray_cli
  ray_cli="$(stage30_find_ray_cli)"
  if [[ -n "${ray_cli}" ]]; then
    "${ray_cli}" stop --force >/dev/null 2>&1 || true
  else
    "${PYTHON_BIN}" - <<'PY' >/dev/null 2>&1 || true
try:
    import ray
    ray.shutdown()
except Exception:
    pass
PY
  fi
}

stage30_validate_tmp_path() {
  local value="$1" label="$2"
  [[ -n "${value}" && "${value}" == /tmp/* && "${value}" != "/tmp" && "${value}" != "/tmp/" ]] || \
    stage30_die "${label} must be a non-root path below /tmp; got: ${value}"
}

stage30_cleanup_runtime() {
  local workspace="${STAGE3_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  local run_root="${STAGE3_TSC_RUN_ROOT:-${workspace}/episode_runs}"
  local ray_tmp="${RAY_TMPDIR:-/tmp/stage3_0_$(id -u)}"
  stage30_validate_tmp_path "${workspace}" "STAGE3_TSC_WORKSPACE_ROOT"
  stage30_validate_tmp_path "${run_root}" "STAGE3_TSC_RUN_ROOT"
  stage30_validate_tmp_path "${ray_tmp}" "RAY_TMPDIR"
  mkdir -p "${workspace}" "${run_root}"
  find "${workspace}" -mindepth 1 -maxdepth 1 -type d \
    \( -name 'stage3_*' -o -name 'stage3_0_*' -o -name 'stage2_*' \) -exec rm -rf -- {} + 2>/dev/null || true
  find "${run_root}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + 2>/dev/null || true
  rm -rf -- "${ray_tmp}" 2>/dev/null || true
}

stage30_runtime_env() {
  export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
  export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
  export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
  export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
  export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-1}"
  export BLIS_NUM_THREADS="${BLIS_NUM_THREADS:-1}"
  export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-1}"
  export PYTHONUNBUFFERED=1
  # The bundled evaluator reads STAGE2_WORKERS; map the Stage3 setting explicitly.
  export STAGE2_WORKERS="${STAGE3_0_WORKERS:-${STAGE2_WORKERS:-96}}"
  export STAGE3_TSC_WORKSPACE_ROOT="${STAGE3_TSC_WORKSPACE_ROOT:-/tmp/tsc_workspace}"
  export STAGE3_TSC_RUN_ROOT="${STAGE3_TSC_RUN_ROOT:-${STAGE3_TSC_WORKSPACE_ROOT}/episode_runs}"
  # Stage2 evaluator/environment storage override names are retained internally.
  export STAGE2_TSC_WORKSPACE_ROOT="${STAGE3_TSC_WORKSPACE_ROOT}"
  export STAGE2_TSC_RUN_ROOT="${STAGE3_TSC_RUN_ROOT}"
  export RAY_TMPDIR="${RAY_TMPDIR:-/tmp/stage3_0_$(id -u)}"
  export TMPDIR="${RAY_TMPDIR}/tmp"
  stage30_validate_tmp_path "${STAGE3_TSC_WORKSPACE_ROOT}" "STAGE3_TSC_WORKSPACE_ROOT"
  stage30_validate_tmp_path "${STAGE3_TSC_RUN_ROOT}" "STAGE3_TSC_RUN_ROOT"
  stage30_validate_tmp_path "${RAY_TMPDIR}" "RAY_TMPDIR"
  mkdir -p "${STAGE3_TSC_WORKSPACE_ROOT}" "${STAGE3_TSC_RUN_ROOT}" "${TMPDIR}"
  ulimit -n 1048576 2>/dev/null || true
  ulimit -u 262144 2>/dev/null || true
}
