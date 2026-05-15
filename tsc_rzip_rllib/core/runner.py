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


def read_total_vessel_current_csv(
    path: Path,
    *,
    column_name: str = "cwire(ka)",
    aggregation: str = "signed_sum",
    raw_to_a: float = 1000.0,
) -> float:
    """Read total vessel/wire current from TSC wire_currents.csv and return Ampere.

    Expected TSC header:
        i/j, xwire, zwire, cwire(ka), cwire0(ka), diff, volts, t-f1

    We intentionally read exactly column_name, default "cwire(ka)".
    If that exact column is missing, raise an error instead of guessing.
    """
    path = Path(path)
    if not path.exists():
        return 0.0

    try:
        df = pd.read_csv(path, skipinitialspace=True)
    except Exception as exc:
        raise RuntimeError(f"Failed to read vessel current CSV: {path}") from exc

    # Normalize only whitespace around column names; do not fuzzy-match.
    df.columns = [str(c).strip() for c in df.columns]
    column_name = str(column_name).strip()

    if column_name not in df.columns:
        raise ValueError(
            f"Required vessel current column {column_name!r} not found in {path}. "
            f"Available columns: {list(df.columns)}"
        )

    vals = pd.to_numeric(df[column_name], errors="coerce").dropna().to_numpy(dtype=float)

    if vals.size == 0:
        return 0.0

    aggregation = str(aggregation).strip().lower()

    if aggregation == "signed_sum":
        total_raw = float(np.sum(vals))
    elif aggregation == "abs_sum":
        total_raw = float(np.sum(np.abs(vals)))
    else:
        raise ValueError(
            "vessel_current_aggregation must be either "
            f"'signed_sum' or 'abs_sum', got {aggregation!r}"
        )

    # cwire(ka) -> A
    return total_raw * float(raw_to_a)


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

    # Vessel-current observation policy
    vessel_current_column: str = "cwire(ka)"
    vessel_current_raw_to_a: float = 1000.0
    vessel_current_aggregation: str = "signed_sum"

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
            vessel_current_column=str(data.get("vessel_current_column", "cwire(ka)")),
            vessel_current_raw_to_a=float(data.get("vessel_current_raw_to_a", 1000.0)),
            vessel_current_aggregation=str(data.get("vessel_current_aggregation", "signed_sum")),
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

        if self.vessel_current_aggregation not in {"signed_sum", "abs_sum"}:
            raise ValueError(
                "vessel_current_aggregation must be either 'signed_sum' or 'abs_sum'."
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

    def _cleanup_runtime_tsc_io(self) -> None:
        """Remove per-step runtime I/O files from the private TSC workdir after collection."""
        if self.cfg.keep_runtime_tsc_outputs:
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

        dst = self.episode_dir / self.cfg.start_folder
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)

        self.current_folder = dst
        self.current_time_ms = self._folder_time_ms(self.cfg.start_folder)
        self.done_reason = None
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

        vessel_current_total_a = read_total_vessel_current_csv(
            folder / "wire_currents.csv",
            column_name=self.cfg.vessel_current_column,
            aggregation=self.cfg.vessel_current_aggregation,
            raw_to_a=self.cfg.vessel_current_raw_to_a,
        )

        abnormal = self._has_abnormal(folder / "outputa")
        if not np.all(np.isfinite([r_state, z_state, g["ip"], vessel_current_total_a])):
            abnormal = True

        return {
            "folder": folder,
            "time_ms": self._folder_time_ms(folder.name),

            "R": float(r_state),
            "Z": float(z_state),
            "Ip": float(g["ip"]),

            # Total vessel/wire current proxy, unit A.
            "vessel_current_total_a": float(vessel_current_total_a),

            "currents_kat_tsc": currents_kat_tsc.astype(float),
            "currents_a_tsc": currents_a_tsc.astype(float),

            "currents_kat_display": tsc_to_display(currents_kat_tsc).astype(float),
            "currents_a_display": tsc_to_display(currents_a_tsc).astype(float),

            "gfile": g,
            "abnormal": bool(abnormal),
            "done_reason": "outputa abnormal exit or non-finite state" if abnormal else "",
        }

    def step_current_a(self, next_current_a_tsc: np.ndarray) -> Dict[str, Any]:
        """Input next-step single-turn coil currents, unit A, TSC order."""
        if self.current_folder is None or self.current_time_ms is None or self.episode_dir is None:
            raise RuntimeError("call reset() before step_current_a()")

        state = self.read_state()
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

        shape_cards = read_card_first_values(self.current_folder / "inputa", [90, 91, 92, 93, 94, 95])
        rows = build_restart_rows(
            current_time_ms=self.current_time_ms,
            dt_ms=self.cfg.dt_ms,
            current_currents_ka=now_current_kat_tsc,
            next_currents_ka=next_current_kat_tsc,
            shape_card_values=shape_cards,
        )
        generate_restart_inputa_file(self.current_folder / "inputa", rows)

        self._copy_runtime_inputs(self.current_folder)
        returncode, stdout, stderr = self._run_tsc()

        if returncode != 0:
            self.done_reason = f"TSC returned non-zero code {returncode}"
            return {
                **state,
                "abnormal": True,
                "done_reason": self.done_reason,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            }

        previous_folder = self.current_folder

        self.current_time_ms += self.cfg.dt_ms
        next_folder = self.episode_dir / f"{self.current_time_ms}ms"

        try:
            self._collect_runtime_outputs(next_folder)
        except Exception as exc:
            self.done_reason = f"TSC output collection failed: {repr(exc)}"
            return {
                **state,
                "abnormal": True,
                "done_reason": self.done_reason,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
            }

        self.current_folder = next_folder

        new_state = self.read_state()
        new_state.update({"returncode": returncode, "stdout": stdout, "stderr": stderr})

        # Cleanup only after new_state is readable and current_folder has valid sprsina.
        self._cleanup_previous_episode_restart(previous_folder, self.current_folder)
        self._cleanup_runtime_tsc_io()

        if new_state["abnormal"]:
            self.done_reason = new_state.get("done_reason", "") or "TSC outputa contains abnormal exit"
            new_state["done_reason"] = self.done_reason

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