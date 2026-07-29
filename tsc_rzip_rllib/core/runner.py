from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .coil_order import (
    DISPLAY_COIL_NAMES,
    TSC_COIL_NAMES,
    display_to_tsc,
    tsc_to_display,
)
from .gfile import parse_gfile, read_coil_currents_csv
from .inputa import build_restart_rows, generate_restart_inputa_file, read_card_first_values


def _try_float(x: str) -> float | None:
    try:
        v = float(str(x).strip())
    except Exception:
        return None

    if not np.isfinite(v):
        return None

    return v


def read_vessel_current_summary_csv(
    path: Path,
    *,
    column_name: str = "cwire(ka)",
    observation_aggregation: str = "signed_sum",
    raw_to_a: float = 1000.0,
) -> Dict[str, float]:
    """Read TSC wire/vessel currents and return low-dimensional summaries in Ampere.

    The deployable observation should normally use only one scalar, the signed
    or configured total current.  For training-time reward/diagnostics we also
    expose abs_sum/rms/max_abs.  These privileged summaries are not required at
    deployment unless the PCS has a vessel-current observer.

    Expected TSC header:
        i/j, xwire, zwire, cwire(ka), cwire0(ka), diff, volts, t-f1
    """
    path = Path(path)
    if not path.exists():
        return {
            "vessel_current_total_a": 0.0,
            "vessel_current_signed_sum_a": 0.0,
            "vessel_current_abs_sum_a": 0.0,
            "vessel_current_rms_a": 0.0,
            "vessel_current_max_abs_a": 0.0,
        }

    try:
        df = pd.read_csv(path, skipinitialspace=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to read vessel current CSV: {path}") from exc

    df.columns = [str(c).strip() for c in df.columns]
    column_name = str(column_name).strip()

    if column_name not in df.columns:
        raise ValueError(
            f"Required vessel current column {column_name!r} not found in {path}. "
            f"Available columns: {list(df.columns)}"
        )

    vals_raw = pd.to_numeric(df[column_name], errors="coerce").dropna().to_numpy(dtype=float)
    if vals_raw.size == 0:
        vals_a = np.zeros(1, dtype=float)
    else:
        vals_a = vals_raw * float(raw_to_a)

    signed_sum_a = float(np.sum(vals_a))
    abs_sum_a = float(np.sum(np.abs(vals_a)))
    rms_a = float(np.sqrt(np.mean(vals_a**2))) if vals_a.size else 0.0
    max_abs_a = float(np.max(np.abs(vals_a))) if vals_a.size else 0.0

    obs_agg = str(observation_aggregation).strip().lower()
    if obs_agg == "signed_sum":
        total_a = signed_sum_a
    elif obs_agg == "abs_sum":
        total_a = abs_sum_a
    elif obs_agg == "rms":
        total_a = rms_a
    elif obs_agg == "max_abs":
        total_a = max_abs_a
    else:
        raise ValueError(
            "vessel_current_observation_aggregation must be one of "
            f"'signed_sum', 'abs_sum', 'rms', 'max_abs', got {obs_agg!r}"
        )

    return {
        "vessel_current_total_a": float(total_a),
        "vessel_current_signed_sum_a": signed_sum_a,
        "vessel_current_abs_sum_a": abs_sum_a,
        "vessel_current_rms_a": rms_a,
        "vessel_current_max_abs_a": max_abs_a,
    }


def read_total_vessel_current_csv(
    path: Path,
    *,
    column_name: str = "cwire(ka)",
    aggregation: str = "signed_sum",
    raw_to_a: float = 1000.0,
) -> float:
    """Backward-compatible scalar vessel-current reader."""
    return float(
        read_vessel_current_summary_csv(
            path,
            column_name=column_name,
            observation_aggregation=aggregation,
            raw_to_a=raw_to_a,
        )["vessel_current_total_a"]
    )

@dataclass
class TSCConfig:
    project_root: Path
    simulation_root: Path

    executable: Path
    tsc_dir: Path
    library_path: str = ""

    start_folder: str = "1100ms"
    run_root: Path = Path("runs")

    dt_ms: int = 5
    state_rz_source: str = "magaxis"
    tsc_timeout_s: float = 120.0

    isolate_tsc_workdir: bool = True
    tsc_workspace_root: Path = Path("tsc_workspaces")

    # Cleanup policy
    keep_episode_restart_files: bool = False
    keep_tsc_workspace: bool = False
    keep_runtime_tsc_outputs: bool = False

    # B99.3 runtime-only mode.  In training we only need the current TSC state,
    # not one large historical folder per RL control step.  When enabled, TSC
    # runs in the private runtime_tsc_dir and the restart file is rolled forward
    # in place.  Current geqdsk/outputa are still generated and read immediately.
    runtime_only_fast_mode: bool = False
    save_step_artifacts: bool = True
    save_artifacts_on_error: bool = True
    save_artifacts_every_n_steps: int = 0

    # Long-training runtime storage policy.  Normal episode directories can be
    # huge because TSC writes restart and diagnostic files at every control step.
    # By default, delete successful/normal episode folders as soon as the episode
    # ends.  Failed episodes may be kept, but only the most recent N are retained.
    cleanup_episode_dir: bool = True
    keep_failed_episode_dir: bool = True
    keep_last_n_failed_episode_dirs: int = 20

    # Vessel-current observation policy
    vessel_current_column: str = "cwire(ka)"
    vessel_current_raw_to_a: float = 1000.0
    vessel_current_aggregation: str = "signed_sum"
    vessel_current_observation_aggregation: str = "signed_sum"

    coil_names_display_order: list[str] = field(default_factory=lambda: DISPLAY_COIL_NAMES.copy())
    coil_names_tsc_order: list[str] = field(default_factory=lambda: TSC_COIL_NAMES.copy())

    turns_display_order: list[float] = field(default_factory=lambda: [1.0] * 14)

    # Single-turn current limits, unit A, DISPLAY order
    min_current_a_display_order: list[float] = field(default_factory=lambda: [-400.0] * 14)
    max_current_a_display_order: list[float] = field(default_factory=lambda: [400.0] * 14)

    # Unified single-turn current slew rate, unit A/ms
    current_slew_a_per_ms: float = 0.03

    @classmethod
    def from_json(cls, path: str | Path) -> "TSCConfig":
        path = Path(path)
        data = json.loads(path.read_text())

        tsc_data = data["tsc"]

        library_path = tsc_data.get("library_path", "")
        if isinstance(library_path, list):
            library_path = ":".join(str(x).rstrip(":") for x in library_path if str(x).strip())
        elif library_path is None:
            library_path = ""
        else:
            library_path = str(library_path)

        cfg = cls(
            project_root=Path(data["project_root"]).expanduser(),
            simulation_root=Path(data["simulation_root"]).expanduser(),
            executable=Path(tsc_data["executable"]).expanduser(),
            tsc_dir=Path(tsc_data["fortran_dir"]).expanduser(),
            library_path=library_path,
            start_folder=data.get("start_folder", "1100ms"),
            run_root=Path(data.get("run_root", "runs")).expanduser(),
            dt_ms=int(data.get("dt_ms", 5)),
            state_rz_source=data.get("state_rz_source", "magaxis"),
            tsc_timeout_s=float(data.get("tsc_timeout_s", 120.0)),
            isolate_tsc_workdir=bool(data.get("isolate_tsc_workdir", True)),
            tsc_workspace_root=Path(data.get("tsc_workspace_root", "tsc_workspaces")).expanduser(),
            keep_episode_restart_files=bool(data.get("keep_episode_restart_files", False)),
            keep_tsc_workspace=bool(data.get("keep_tsc_workspace", False)),
            keep_runtime_tsc_outputs=bool(data.get("keep_runtime_tsc_outputs", False)),
            runtime_only_fast_mode=bool(data.get("runtime_only_fast_mode", False)),
            save_step_artifacts=bool(data.get("save_step_artifacts", True)),
            save_artifacts_on_error=bool(data.get("save_artifacts_on_error", True)),
            save_artifacts_every_n_steps=int(data.get("save_artifacts_every_n_steps", 0)),
            cleanup_episode_dir=bool(data.get("cleanup_episode_dir", True)),
            keep_failed_episode_dir=bool(data.get("keep_failed_episode_dir", True)),
            keep_last_n_failed_episode_dirs=int(data.get("keep_last_n_failed_episode_dirs", 20)),
            vessel_current_column=str(data.get("vessel_current_column", "cwire(ka)")),
            vessel_current_raw_to_a=float(data.get("vessel_current_raw_to_a", 1000.0)),
            vessel_current_aggregation=str(data.get("vessel_current_aggregation", "signed_sum")),
            vessel_current_observation_aggregation=str(data.get("vessel_current_observation_aggregation", data.get("vessel_current_aggregation", "signed_sum"))),
            coil_names_display_order=data["coil_names_display_order"],
            coil_names_tsc_order=data["coil_names_tsc_order"],
            turns_display_order=data["turns_display_order"],
            min_current_a_display_order=data["min_current_a_display_order"],
            max_current_a_display_order=data["max_current_a_display_order"],
            current_slew_a_per_ms=float(data["current_slew_a_per_ms"]),
        )

        cfg.validate()
        return cfg

    def validate(self) -> None:
        if self.coil_names_display_order != DISPLAY_COIL_NAMES:
            raise ValueError(f"coil_names_display_order is wrong. Expected:\n{DISPLAY_COIL_NAMES}")

        if self.coil_names_tsc_order != TSC_COIL_NAMES:
            raise ValueError(f"coil_names_tsc_order is wrong. Expected:\n{TSC_COIL_NAMES}")

        self._check_14(self.turns_display_order, "turns_display_order")
        self._check_14(self.min_current_a_display_order, "min_current_a_display_order")
        self._check_14(self.max_current_a_display_order, "max_current_a_display_order")

        turns = np.asarray(self.turns_display_order, dtype=float)
        if np.any(turns <= 0):
            raise ValueError("turns_display_order must be positive for every coil.")

        min_i = np.asarray(self.min_current_a_display_order, dtype=float)
        max_i = np.asarray(self.max_current_a_display_order, dtype=float)
        if np.any(max_i <= min_i):
            raise ValueError(
                "Every max_current_a_display_order value must be greater than "
                "min_current_a_display_order."
            )

        if self.current_slew_a_per_ms <= 0:
            raise ValueError("current_slew_a_per_ms must be positive.")

        if self.tsc_timeout_s <= 0:
            raise ValueError("tsc_timeout_s must be positive.")

        if self.vessel_current_raw_to_a <= 0:
            raise ValueError("vessel_current_raw_to_a must be positive.")

        if self.keep_last_n_failed_episode_dirs < 0:
            raise ValueError("keep_last_n_failed_episode_dirs must be >= 0.")

        if self.save_artifacts_every_n_steps < 0:
            raise ValueError("save_artifacts_every_n_steps must be >= 0.")

        if self.vessel_current_aggregation not in {"signed_sum", "abs_sum", "rms", "max_abs"}:
            raise ValueError(
                "vessel_current_aggregation must be one of signed_sum, abs_sum, rms, max_abs."
            )

        if self.vessel_current_observation_aggregation not in {"signed_sum", "abs_sum", "rms", "max_abs"}:
            raise ValueError(
                "vessel_current_observation_aggregation must be one of signed_sum, abs_sum, rms, max_abs."
            )

        if not self.vessel_current_column.strip():
            raise ValueError("vessel_current_column must be a non-empty string.")

        if not self.executable.exists():
            raise FileNotFoundError(f"TSC executable not found: {self.executable}")

        if not self.tsc_dir.exists():
            raise FileNotFoundError(f"TSC working directory not found: {self.tsc_dir}")

        if not self.simulation_root.exists():
            raise FileNotFoundError(f"simulation_root not found: {self.simulation_root}")

    @staticmethod
    def _check_14(x, name: str) -> None:
        if len(x) != 14:
            raise ValueError(f"{name} must have length 14, got {len(x)}")

    def resolved_run_root(self) -> Path:
        return self.run_root if self.run_root.is_absolute() else self.project_root / self.run_root

    def resolved_tsc_workspace_root(self) -> Path:
        if self.tsc_workspace_root.is_absolute():
            return self.tsc_workspace_root
        return self.project_root / self.tsc_workspace_root

    @property
    def turns_display(self) -> np.ndarray:
        return np.asarray(self.turns_display_order, dtype=float)

    @property
    def turns_tsc(self) -> np.ndarray:
        return display_to_tsc(self.turns_display)

    @property
    def min_current_a_tsc(self) -> np.ndarray:
        return display_to_tsc(np.asarray(self.min_current_a_display_order, dtype=float))

    @property
    def max_current_a_tsc(self) -> np.ndarray:
        return display_to_tsc(np.asarray(self.max_current_a_display_order, dtype=float))

    @property
    def max_delta_current_a_per_step(self) -> float:
        """Unified single-turn current step limit, unit A/step."""
        return self.current_slew_a_per_ms * self.dt_ms


class TSCStepRunner:
    """One-step-at-a-time TSC runner.

    External/config/RL/UI:
        single-turn coil current, unit A

    TSC card 15 / coil_currents.csv:
        kA-turn

    wire_currents.csv:
        cwire(ka), converted to A before entering RL observation
    """

    def __init__(
        self,
        config: TSCConfig,
        worker_id: str | None = None,
        keep_workspace: bool | None = None,
    ):
        self.cfg = config
        self.worker_id = worker_id or f"worker_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        self.keep_workspace = bool(self.cfg.keep_tsc_workspace if keep_workspace is None else keep_workspace)

        self.episode_dir: Optional[Path] = None
        self.current_folder: Optional[Path] = None
        self.current_time_ms: Optional[int] = None
        self.done_reason: Optional[str] = None
        self.local_step_index: int = 0
        self.last_step_timing: Dict[str, float] = {}
        # One-shot, worker-local snapshot requests used by restart validation.
        # The request is consumed only after TSC has produced and promoted the
        # restart state for the requested local step.
        self._restart_snapshot_requests: Dict[int, Path] = {}

        self.runtime_tsc_dir: Path = self._prepare_runtime_tsc_dir()
        self.runtime_executable: Path = self._resolve_runtime_executable()

    @property
    def turns_tsc(self) -> np.ndarray:
        return self.cfg.turns_tsc

    @property
    def max_delta_current_a_per_step(self) -> float:
        return self.cfg.max_delta_current_a_per_step

    @property
    def max_delta_current_kat_per_step_tsc(self) -> np.ndarray:
        """TSC-side per-coil step limit, unit kA-turn/step."""
        return self.cfg.max_delta_current_a_per_step * self.turns_tsc / 1000.0

    @property
    def min_current_a_tsc(self) -> np.ndarray:
        return self.cfg.min_current_a_tsc

    @property
    def max_current_a_tsc(self) -> np.ndarray:
        return self.cfg.max_current_a_tsc

    @staticmethod
    def current_a_to_kat(current_a_tsc: np.ndarray, turns_tsc: np.ndarray) -> np.ndarray:
        """A -> kA-turn, TSC order."""
        return np.asarray(current_a_tsc, dtype=float) * np.asarray(turns_tsc, dtype=float) / 1000.0

    @staticmethod
    def current_kat_to_a(current_kat_tsc: np.ndarray, turns_tsc: np.ndarray) -> np.ndarray:
        """kA-turn -> A, TSC order."""
        turns = np.asarray(turns_tsc, dtype=float)
        if np.any(np.isclose(turns, 0.0)):
            raise ValueError("turns contains zero, cannot convert kA-turn to A.")
        return np.asarray(current_kat_tsc, dtype=float) * 1000.0 / turns

    def _prepare_runtime_tsc_dir(self) -> Path:
        if not self.cfg.isolate_tsc_workdir:
            return self.cfg.tsc_dir

        root = self.cfg.resolved_tsc_workspace_root()
        root.mkdir(parents=True, exist_ok=True)

        runtime_dir = root / f"{self.worker_id}_{uuid.uuid4().hex[:8]}"

        if runtime_dir.exists():
            shutil.rmtree(runtime_dir)

        shutil.copytree(
            self.cfg.tsc_dir,
            runtime_dir,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                "inputa",
                "sprsina",
                "sprsoua",
                "geqdsk",
                "outputa",
                "coil_currents.csv",
                "wire_currents.csv",
                "tsc.cgm",
                "*.log",
                "__pycache__",
            ),
        )

        return runtime_dir

    def _resolve_runtime_executable(self) -> Path:
        try:
            rel = self.cfg.executable.relative_to(self.cfg.tsc_dir)
            candidate = self.runtime_tsc_dir / rel
            if candidate.exists():
                return candidate
        except ValueError:
            pass

        return self.cfg.executable

    def cleanup_runtime_workspace(self) -> None:
        if self.cfg.isolate_tsc_workdir and not self.keep_workspace:
            if self.runtime_tsc_dir.exists():
                shutil.rmtree(self.runtime_tsc_dir, ignore_errors=True)

    def cleanup_episode_workspace(self, *, failed: bool = False, reason: str = "") -> None:
        """Cleanup the current per-episode directory according to config policy.

        Normal episodes are deleted immediately to prevent long trainings from
        filling /home with thousands of TSC restart/output folders.  Failed
        episodes can be kept for debugging, but only the most recent
        keep_last_n_failed_episode_dirs directories containing a failure marker
        are retained.  Cleanup is best-effort and must never crash training.
        """
        episode_dir = self.episode_dir
        self.episode_dir = None
        self.current_folder = None
        self.current_time_ms = None
        self.local_step_index = 0

        if episode_dir is None or not Path(episode_dir).exists():
            return

        episode_dir = Path(episode_dir)
        try:
            if failed and self.cfg.keep_failed_episode_dir and self.cfg.keep_last_n_failed_episode_dirs > 0:
                marker = episode_dir / "_FAILED_REASON.txt"
                marker.write_text(str(reason or self.done_reason or "failed"), encoding="utf-8", errors="ignore")
                self._prune_failed_episode_dirs()
                return

            if self.cfg.cleanup_episode_dir:
                shutil.rmtree(episode_dir, ignore_errors=True)
        except Exception:
            # Never let cleanup failure crash a worker. Disk watchdog will catch
            # persistent cleanup problems at the training loop level.
            pass

    def _prune_failed_episode_dirs(self) -> None:
        keep_n = int(self.cfg.keep_last_n_failed_episode_dirs)
        if keep_n < 0:
            keep_n = 0

        run_root = self.cfg.resolved_run_root()
        if not run_root.exists():
            return

        failed_dirs: list[Path] = []
        try:
            for marker in run_root.glob("*/_FAILED_REASON.txt"):
                if marker.parent.is_dir():
                    failed_dirs.append(marker.parent)
        except Exception:
            return

        failed_dirs.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0.0, reverse=True)
        for old_dir in failed_dirs[keep_n:]:
            try:
                shutil.rmtree(old_dir, ignore_errors=True)
            except Exception:
                pass

    def _safe_unlink(self, path: Path) -> None:
        """Delete one file if it exists. Cleanup failure must never crash training."""
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except Exception:
            pass

    def _cleanup_previous_episode_restart(self, previous_folder: Path, current_folder: Path) -> None:
        """Delete old restart file only after the new current folder has its own sprsina."""
        if self.cfg.keep_episode_restart_files:
            return

        previous_folder = Path(previous_folder)
        current_folder = Path(current_folder)

        if previous_folder == current_folder:
            return

        # Must keep the latest restart.
        if not (current_folder / "sprsina").exists():
            return

        # Extra guard: never touch the source start folder.
        source_start = (self.cfg.simulation_root / self.cfg.start_folder).resolve()
        try:
            if previous_folder.resolve() == source_start:
                return
        except Exception:
            return

        self._safe_unlink(previous_folder / "sprsina")

    def _cleanup_runtime_tsc_io(self, *, force: bool = False) -> None:
        """Remove per-step runtime I/O files from the private TSC workdir after collection."""
        if self.cfg.keep_runtime_tsc_outputs and not force:
            return

        for name in [
            "inputa",
            "sprsina",
            "sprsoua",
            "geqdsk",
            "outputa",
            "tsc.cgm",
            "coil_currents.csv",
            "wire_currents.csv",
        ]:
            self._safe_unlink(self.runtime_tsc_dir / name)

    def reset(self, episode_name: Optional[str] = None) -> Dict[str, Any]:
        src = self.cfg.simulation_root / self.cfg.start_folder
        if not src.exists():
            raise FileNotFoundError(f"start folder not found: {src}")

        sprsina = src / "sprsina"
        if not sprsina.exists():
            raise FileNotFoundError(f"{sprsina} is required for restart.")

        episode_name = episode_name or datetime.now().strftime("episode_%Y%m%d_%H%M%S")
        self.episode_dir = self.cfg.resolved_run_root() / episode_name
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        self.current_time_ms = self._folder_time_ms(self.cfg.start_folder)
        self.done_reason = None
        self.local_step_index = 0
        self.last_step_timing = {}

        if self.cfg.runtime_only_fast_mode:
            t0 = datetime.now()
            self._cleanup_runtime_tsc_io(force=True)
            copy_t0 = datetime.now()
            # Minimal current-state inputs/outputs needed for the first observation.
            # geqdsk/outputa/coil/wire are read by read_state(); inputa/sprsina are
            # needed by the first TSC restart step.  Missing optional outputs are
            # allowed only if read_state() does not require them in the user's setup.
            for name in ["inputa", "sprsina", "geqdsk", "outputa", "coil_currents.csv", "wire_currents.csv"]:
                src_file = src / name
                if src_file.exists():
                    shutil.copy2(src_file, self.runtime_tsc_dir / name)
                elif name in {"inputa", "sprsina", "geqdsk", "coil_currents.csv"}:
                    raise FileNotFoundError(f"required runtime-only reset file missing: {src_file}")
            self.current_folder = self.runtime_tsc_dir
            dt = (datetime.now() - t0).total_seconds()
            copy_dt = (datetime.now() - copy_t0).total_seconds()
            self.last_step_timing = {"reset_total_s": float(dt), "reset_copy_inputs_s": float(copy_dt), "runtime_only": 1.0}
            return self.read_state()

        dst = self.episode_dir / self.cfg.start_folder
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        self.current_folder = dst
        return self.read_state()

    def read_state(self) -> Dict[str, Any]:
        if self.current_folder is None:
            raise RuntimeError("call reset() before read_state()")
        return self._read_state_from_folder(self.current_folder)

    def _read_state_from_folder(self, folder: Path) -> Dict[str, Any]:
        g = parse_gfile(folder / "geqdsk")

        # TSC output order, unit kA-turn
        currents_kat_tsc = read_coil_currents_csv(folder / "coil_currents.csv")
        if currents_kat_tsc.shape != (14,):
            raise ValueError(f"expected 14 coil currents, got {currents_kat_tsc.shape}")

        # Convert to the project-wide unit: single-turn A
        currents_a_tsc = self.current_kat_to_a(currents_kat_tsc, self.turns_tsc)

        if self.cfg.state_rz_source == "magaxis":
            r_state, z_state = g["xmag"], g["zmag"]
        else:
            r_state, z_state = g["rc"], g["zc"]

        vessel_summary = read_vessel_current_summary_csv(
            folder / "wire_currents.csv",
            column_name=self.cfg.vessel_current_column,
            observation_aggregation=self.cfg.vessel_current_observation_aggregation,
            raw_to_a=self.cfg.vessel_current_raw_to_a,
        )

        abnormal = self._has_abnormal(folder / "outputa")
        finite_check = [r_state, z_state, g["ip"]] + list(vessel_summary.values())
        if not np.all(np.isfinite(finite_check)):
            abnormal = True

        return {
            "folder": folder,
            "time_ms": int(self.current_time_ms) if (self.cfg.runtime_only_fast_mode and self.current_time_ms is not None) else self._folder_time_ms(folder.name),

            "R": float(r_state),
            "Z": float(z_state),
            "Ip": float(g["ip"]),

            # Deployable scalar vessel/wire-current observation proxy, unit A.
            **vessel_summary,

            "currents_kat_tsc": currents_kat_tsc.astype(float),
            "currents_a_tsc": currents_a_tsc.astype(float),

            "currents_kat_display": tsc_to_display(currents_kat_tsc).astype(float),
            "currents_a_display": tsc_to_display(currents_a_tsc).astype(float),

            "gfile": g,
            "runner_timing": dict(self.last_step_timing),
            "runtime_only_fast_mode": bool(self.cfg.runtime_only_fast_mode),
            "abnormal": bool(abnormal),
            "done_reason": "outputa abnormal exit or non-finite state" if abnormal else "",
        }

    def step_current_a(self, next_current_a_tsc: np.ndarray) -> Dict[str, Any]:
        """Input next-step single-turn coil currents, unit A, TSC order."""
        step_wall_t0 = datetime.now()
        timing: Dict[str, float] = {"runtime_only": 1.0 if self.cfg.runtime_only_fast_mode else 0.0}
        if self.current_folder is None or self.current_time_ms is None or self.episode_dir is None:
            raise RuntimeError("call reset() before step_current_a()")

        read0_t0 = datetime.now()
        state = self.read_state()
        timing["read_state_before_s"] = float((datetime.now() - read0_t0).total_seconds())
        now_current_kat_tsc = state["currents_kat_tsc"]

        next_current_a_tsc = np.asarray(next_current_a_tsc, dtype=float)
        if next_current_a_tsc.shape != (14,):
            raise ValueError(f"next_current_a_tsc must have shape (14,), got {next_current_a_tsc.shape}")

        next_current_a_tsc = np.clip(
            next_current_a_tsc,
            self.min_current_a_tsc,
            self.max_current_a_tsc,
        )

        # Only here do we convert A to kA-turn for TSC.
        next_current_kat_tsc = self.current_a_to_kat(next_current_a_tsc, self.turns_tsc)

        write_t0 = datetime.now()
        shape_cards = read_card_first_values(self.current_folder / "inputa", [90, 91, 92, 93, 94, 95])
        rows = build_restart_rows(
            current_time_ms=self.current_time_ms,
            dt_ms=self.cfg.dt_ms,
            current_currents_ka=now_current_kat_tsc,
            next_currents_ka=next_current_kat_tsc,
            shape_card_values=shape_cards,
        )
        generate_restart_inputa_file(self.current_folder / "inputa", rows)
        timing["write_input_s"] = float((datetime.now() - write_t0).total_seconds())

        copy_in_t0 = datetime.now()
        if not self.cfg.runtime_only_fast_mode:
            self._copy_runtime_inputs(self.current_folder)
        timing["copy_runtime_inputs_s"] = float((datetime.now() - copy_in_t0).total_seconds())

        run_t0 = datetime.now()
        returncode, stdout, stderr = self._run_tsc()
        timing["gotsc_subprocess_s"] = float((datetime.now() - run_t0).total_seconds())

        if returncode != 0:
            self.done_reason = f"TSC returned non-zero code {returncode}"
            timing["step_total_s"] = float((datetime.now() - step_wall_t0).total_seconds())
            self.last_step_timing = timing
            self._save_runtime_artifacts_on_error("nonzero_returncode")
            return {
                **state,
                "runner_timing": dict(timing),
                "abnormal": True,
                "done_reason": self.done_reason,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            }

        previous_folder = self.current_folder
        self.current_time_ms += self.cfg.dt_ms
        self.local_step_index += 1

        if self.cfg.runtime_only_fast_mode:
            restart_t0 = datetime.now()
            try:
                self._roll_runtime_restart_forward()
            except Exception as exc:
                self.done_reason = f"TSC restart update failed: {repr(exc)}"
                timing["restart_update_s"] = float((datetime.now() - restart_t0).total_seconds())
                timing["step_total_s"] = float((datetime.now() - step_wall_t0).total_seconds())
                self.last_step_timing = timing
                self._save_runtime_artifacts_on_error("restart_update_failed")
                return {
                    **state,
                    "runner_timing": dict(timing),
                    "abnormal": True,
                    "done_reason": self.done_reason,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            timing["restart_update_s"] = float((datetime.now() - restart_t0).total_seconds())

            save_t0 = datetime.now()
            self._maybe_save_runtime_step_artifacts()
            timing["save_artifacts_s"] = float((datetime.now() - save_t0).total_seconds())
            self.current_folder = self.runtime_tsc_dir
        else:
            next_folder = self.episode_dir / f"{self.current_time_ms}ms"
            collect_t0 = datetime.now()
            try:
                self._collect_runtime_outputs(next_folder)
            except Exception as exc:
                self.done_reason = f"TSC output collection failed: {repr(exc)}"
                timing["collect_outputs_s"] = float((datetime.now() - collect_t0).total_seconds())
                timing["step_total_s"] = float((datetime.now() - step_wall_t0).total_seconds())
                self.last_step_timing = timing
                self._save_runtime_artifacts_on_error("collect_outputs_failed")
                return {
                    **state,
                    "runner_timing": dict(timing),
                    "abnormal": True,
                    "done_reason": self.done_reason,
                    "returncode": returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                }
            timing["collect_outputs_s"] = float((datetime.now() - collect_t0).total_seconds())
            self.current_folder = next_folder
            save_t0 = datetime.now()
            self._maybe_save_runtime_step_artifacts()
            timing["save_artifacts_s"] = float((datetime.now() - save_t0).total_seconds())

        read1_t0 = datetime.now()
        self.last_step_timing = timing
        new_state = self.read_state()
        timing["read_state_after_s"] = float((datetime.now() - read1_t0).total_seconds())
        timing["step_total_s"] = float((datetime.now() - step_wall_t0).total_seconds())
        self.last_step_timing = timing
        new_state["runner_timing"] = dict(timing)
        new_state.update({"returncode": returncode, "stdout": stdout, "stderr": stderr})

        if not self.cfg.runtime_only_fast_mode:
            # Cleanup only after new_state is readable and current_folder has valid sprsina.
            self._cleanup_previous_episode_restart(previous_folder, self.current_folder)
            self._cleanup_runtime_tsc_io()

        if new_state["abnormal"]:
            self.done_reason = new_state.get("done_reason", "") or "TSC outputa contains abnormal exit"
            new_state["done_reason"] = self.done_reason
            self._save_runtime_artifacts_on_error("abnormal_output")

        return new_state

    def step_delta_current_a(self, delta_current_a_tsc: np.ndarray) -> Dict[str, Any]:
        """Input single-turn coil-current increments, unit A, TSC order."""
        state = self.read_state()

        delta = np.asarray(delta_current_a_tsc, dtype=float)
        if delta.shape != (14,):
            raise ValueError(f"delta_current_a_tsc must have shape (14,), got {delta.shape}")

        max_delta = self.max_delta_current_a_per_step
        delta = np.clip(delta, -max_delta, max_delta)

        next_current_a_tsc = state["currents_a_tsc"] + delta
        return self.step_current_a(next_current_a_tsc)

    # Compatibility aliases
    def step(self, next_currents_a: np.ndarray) -> Dict[str, Any]:
        return self.step_current_a(next_currents_a)

    def step_delta(self, delta_currents_a: np.ndarray) -> Dict[str, Any]:
        return self.step_delta_current_a(delta_currents_a)

    def _copy_runtime_inputs(self, folder: Path) -> None:
        self.runtime_tsc_dir.mkdir(parents=True, exist_ok=True)

        for name in ["inputa", "sprsina"]:
            src = folder / name
            if not src.exists():
                raise FileNotFoundError(f"required runtime input missing: {src}")
            shutil.copy2(src, self.runtime_tsc_dir / name)

    def _collect_runtime_outputs(self, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)

        for name in ["inputa", "geqdsk", "outputa", "tsc.cgm", "coil_currents.csv", "wire_currents.csv"]:
            src = self.runtime_tsc_dir / name
            if src.exists():
                shutil.copy2(src, dst / name)

        sprsoua = self.runtime_tsc_dir / "sprsoua"
        if sprsoua.exists():
            shutil.copy2(sprsoua, dst / "sprsina")
        else:
            raise FileNotFoundError(f"TSC did not produce restart file: {sprsoua}")

    def _roll_runtime_restart_forward(self) -> None:
        """Update runtime sprsina from the just-produced sprsoua.

        B99.3 intentionally uses copy2 rather than os.replace for the first
        runtime-only version.  This keeps sprsoua available for debugging and
        avoids relying on undocumented TSC file-retention assumptions.
        """
        sprsoua = self.runtime_tsc_dir / "sprsoua"
        if not sprsoua.exists():
            raise FileNotFoundError(f"TSC did not produce restart file: {sprsoua}")
        shutil.copy2(sprsoua, self.runtime_tsc_dir / "sprsina")

    def _runtime_artifact_dir(self, tag: str) -> Path:
        base = self.episode_dir or self.cfg.resolved_run_root()
        return Path(base) / f"runtime_artifacts_{tag}_{self.current_time_ms}ms"

    def _copy_runtime_artifacts_to(self, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for name in [
            "inputa",
            "sprsina",
            "sprsoua",
            "geqdsk",
            "outputa",
            "tsc.cgm",
            "coil_currents.csv",
            "wire_currents.csv",
        ]:
            src = self.runtime_tsc_dir / name
            if src.exists():
                shutil.copy2(src, dst / name)

    def request_restart_snapshot(
        self,
        *,
        local_step_index: int,
        destination: Path,
    ) -> None:
        """Register a one-shot authentic TSC restart snapshot.

        The snapshot is exported *after* the requested TSC step has completed
        and ``sprsoua`` has been promoted to the current ``sprsina``.  Requests
        are worker-local and are intentionally not inferred from observations.
        """
        index = int(local_step_index)
        if index <= 0:
            raise ValueError("restart snapshot local_step_index must be positive")
        destination = Path(destination).expanduser().resolve()
        previous = self._restart_snapshot_requests.get(index)
        if previous is not None and previous != destination:
            raise ValueError(
                f"restart snapshot step {index} already targets {previous}"
            )
        self._restart_snapshot_requests[index] = destination

    def clear_restart_snapshot_requests(self) -> None:
        """Remove unconsumed snapshot requests between independent episodes."""
        self._restart_snapshot_requests.clear()

    def export_restart_snapshot(self, destination: Path) -> Dict[str, Any]:
        """Copy the current complete TSC restart state into ``destination``."""
        if self.current_time_ms is None or self.current_folder is None:
            raise RuntimeError("call reset() and advance TSC before exporting a restart")
        destination = Path(destination).expanduser().resolve()
        destination.mkdir(parents=True, exist_ok=True)
        if self.cfg.runtime_only_fast_mode:
            self._copy_runtime_artifacts_to(destination)
        else:
            for name in [
                "inputa",
                "sprsina",
                "sprsoua",
                "geqdsk",
                "outputa",
                "tsc.cgm",
                "coil_currents.csv",
                "wire_currents.csv",
            ]:
                src = Path(self.current_folder) / name
                if src.exists():
                    shutil.copy2(src, destination / name)
        required = [
            "inputa",
            "sprsina",
            "geqdsk",
            "coil_currents.csv",
            "wire_currents.csv",
        ]
        missing = [name for name in required if not (destination / name).is_file()]
        if missing:
            raise FileNotFoundError(
                f"restart snapshot missing required files: {missing}"
            )
        return {
            "destination": str(destination),
            "local_step_index": int(self.local_step_index),
            "time_ms": int(self.current_time_ms),
            "files": sorted(path.name for path in destination.iterdir() if path.is_file()),
        }

    def _maybe_save_runtime_step_artifacts(self) -> None:
        requested = self._restart_snapshot_requests.pop(
            int(self.local_step_index), None
        )
        if requested is not None:
            self.export_restart_snapshot(requested)
        if not self.cfg.runtime_only_fast_mode:
            return
        if self.cfg.save_step_artifacts:
            self._copy_runtime_artifacts_to(self._runtime_artifact_dir("step"))
            return
        n = int(self.cfg.save_artifacts_every_n_steps)
        if n > 0 and self.local_step_index > 0 and self.local_step_index % n == 0:
            self._copy_runtime_artifacts_to(self._runtime_artifact_dir("sample"))

    def _save_runtime_artifacts_on_error(self, tag: str) -> None:
        if not self.cfg.save_artifacts_on_error:
            return
        try:
            self._copy_runtime_artifacts_to(self._runtime_artifact_dir(f"failed_{tag}"))
        except Exception:
            pass

    def _run_tsc(self) -> tuple[int, str, str]:
        env = os.environ.copy()
        if self.cfg.library_path:
            env["LD_LIBRARY_PATH"] = self.cfg.library_path + ":" + env.get("LD_LIBRARY_PATH", "")

        try:
            proc = subprocess.run(
                [str(self.runtime_executable)],
                cwd=str(self.runtime_tsc_dir),
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=self.cfg.tsc_timeout_s,
            )
            return proc.returncode, proc.stdout, proc.stderr

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            return -999, stdout, f"TSC timeout after {self.cfg.tsc_timeout_s} s. {stderr}"

    @staticmethod
    def _folder_time_ms(name: str) -> int:
        return int(name.rstrip("ms"))

    @staticmethod
    def _has_abnormal(path: Path) -> bool:
        if not path.exists():
            return False
        return "abnormal exit" in path.read_text(errors="ignore").lower()