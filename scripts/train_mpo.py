#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import os
import resource
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Safety defaults before importing Ray/Torch.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_THREADS", "1")
os.environ.setdefault("TORCH_NUM_INTEROP_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")
os.environ.setdefault("RAYON_NUM_THREADS", "1")
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")

import numpy as np
import ray
import torch
import torch.nn.functional as F

from tsc_rzip_rllib.envs.rllib_env import RllibTscRzipEnv
from tsc_rzip_rllib.mpo.models import (
    RecurrentGaussianActor,
    RecurrentQCritic,
    gaussian_kl,
    hard_update,
    soft_update,
    tanh_gaussian_log_prob,
)
from tsc_rzip_rllib.mpo.privileged import build_privileged_vector, privileged_dim
from tsc_rzip_rllib.mpo.replay import SequenceReplayBuffer
from tsc_rzip_rllib.mpo.constrained_dual import MultiplicativeDuals
from tsc_rzip_rllib.utils.config import deep_update, load_json


def json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {str(k): json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [json_safe(x) for x in obj]
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return str(obj)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def expand_macros(obj: Any, macros: dict[str, str]) -> Any:
    if isinstance(obj, str):
        out = os.path.expandvars(obj)
        for k, v in macros.items():
            out = out.replace("{" + k + "}", str(v))
        return out
    if isinstance(obj, list):
        return [expand_macros(x, macros) for x in obj]
    if isinstance(obj, dict):
        return {k: expand_macros(v, macros) for k, v in obj.items()}
    return obj




def default_macros(run_id: str) -> dict[str, str]:
    tsc_all_root = os.environ.get("TSC_ALL_ROOT")
    if not tsc_all_root:
        # Project layout: /.../tsc_all/tsc_rzip_rllib/scripts/train_mpo.py
        tsc_all_root = str(PROJECT_DIR.parent)
    return {
        "USER": os.environ.get("USER", "user"),
        "RUN_ID": str(run_id),
        "TSC_ALL_ROOT": str(Path(tsc_all_root).expanduser()),
        "PROJECT_DIR": str(PROJECT_DIR),
    }


def resolve_path_maybe_relative(path_text: str, *, base_dir: Path = PROJECT_DIR) -> Path:
    p = Path(str(path_text)).expanduser()
    if not p.is_absolute():
        p = base_dir / p
    return p


def resolve_tsc_config_file(train_cfg: dict[str, Any], *, out_dir: Path, macros: dict[str, str]) -> dict[str, Any]:
    """Resolve nested env_config JSON macros and point train_cfg to a concrete file.

    The outer train config is already expanded, but env_config points to another
    JSON file (usually configs/tsc_low_field_side_118.json).  That nested file
    can contain placeholders such as {TSC_ALL_ROOT}, ${TSC_ALL_ROOT}, {USER},
    and {RUN_ID}.  TSCConfig.from_json() validates paths directly and does not
    expand those placeholders, so we must materialize a resolved copy before
    constructing any environment.
    """
    cfg = json.loads(json.dumps(train_cfg))
    if "env_config" not in cfg:
        raise KeyError("train_cfg must contain 'env_config'.")

    env_config_path = resolve_path_maybe_relative(expand_macros(str(cfg["env_config"]), macros))
    if not env_config_path.exists():
        raise FileNotFoundError(
            f"env_config JSON not found after macro expansion: {env_config_path}\n"
            f"TSC_ALL_ROOT={macros.get('TSC_ALL_ROOT')}"
        )

    nested = load_json(env_config_path)
    nested = expand_macros(nested, macros)

    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_path = out_dir / f"{env_config_path.stem}.resolved.json"
    with open(resolved_path, "w", encoding="utf-8") as f:
        json.dump(json_safe(nested), f, indent=2, ensure_ascii=False)

    cfg["env_config"] = str(resolved_path)
    cfg.setdefault("_resolved_external_configs", {})["env_config_original"] = str(env_config_path)
    cfg["_resolved_external_configs"]["env_config_resolved"] = str(resolved_path)
    cfg["_resolved_macros"] = dict(macros)
    return cfg

def load_merged_json(path: Path, override_path: Path | None = None) -> dict[str, Any]:
    cfg = load_json(path)
    if override_path is not None:
        cfg = deep_update(cfg, load_json(override_path))
    return cfg


def ray_worker_env_vars() -> dict[str, str]:
    keys = [
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "TORCH_NUM_THREADS",
        "TORCH_NUM_INTEROP_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
        "RAYON_NUM_THREADS",
        "RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO",
    ]
    return {k: os.environ.get(k, "1") for k in keys}


def available_cpu_count() -> int:
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except Exception:
        return max(1, os.cpu_count() or 1)


def disk_health_report(paths: list[Path]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for p in paths:
        try:
            p = Path(p).expanduser()
            p.mkdir(parents=True, exist_ok=True)
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            usage = shutil.disk_usage(p)
            st = os.statvfs(str(p))
            inode_pct = 100.0 * float(st.f_favail / st.f_files) if st.f_files > 0 else 100.0
            out.append(
                {
                    "path": key,
                    "free_gb": float(usage.free / (1024**3)),
                    "used_percent": float(100.0 * usage.used / max(usage.total, 1)),
                    "free_inodes": int(st.f_favail),
                    "total_inodes": int(st.f_files),
                    "inode_free_percent": inode_pct,
                }
            )
        except Exception as exc:
            out.append({"path": str(p), "error": repr(exc)})
    return out


def piecewise_constant_schedule(schedule: Any, step: int, default: float) -> float:
    """Return the last value whose threshold step has been reached.

    Accepts [[step, value], ...] or [{"step": ..., "value": ...}, ...].
    This is intentionally piecewise-constant so it is easy to reason about
    safety limits in control experiments.
    """
    if not schedule:
        return float(default)
    pairs: list[tuple[int, float]] = []
    for item in schedule:
        try:
            if isinstance(item, dict):
                pairs.append((int(item.get("step", item.get("env_steps", 0))), float(item.get("value", item.get("scale")))))
            else:
                pairs.append((int(item[0]), float(item[1])))
        except Exception:
            continue
    if not pairs:
        return float(default)
    pairs.sort(key=lambda x: x[0])
    out = float(default)
    for threshold, value in pairs:
        if int(step) >= int(threshold):
            out = float(value)
        else:
            break
    return float(out)



def sanitize_metric_name(name: str) -> str:
    out = []
    for ch in str(name):
        if ch.isalnum() or ch in {"_", "-"}:
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip("_") or "unnamed"


def action_names_from_cfg(cfg: dict[str, Any], action_dim: int) -> list[str]:
    train_cfg = cfg.get("train_config_resolved", {}) if isinstance(cfg, dict) else {}
    env_path = train_cfg.get("env_config") if isinstance(train_cfg, dict) else None
    names: list[str] = []
    if env_path:
        try:
            env_cfg = load_json(resolve_path_maybe_relative(str(env_path), base_dir=PROJECT_DIR))
            names = [str(x) for x in env_cfg.get("coil_names_display_order", [])]
        except Exception:
            names = []
    if len(names) != int(action_dim):
        names = [f"a{i:02d}" for i in range(int(action_dim))]
    return [sanitize_metric_name(x) for x in names]


def stage_env_params_for_steps(train_cfg: dict[str, Any], env_steps: int) -> dict[str, Any]:
    """Return curriculum env_params active at a given global env-step count.

    This mirrors the piecewise curriculum style used by the environment configs and
    is also used by the lightweight extra reward wrapper below.  If no curriculum
    is enabled, it returns an empty dict.
    """
    cur = train_cfg.get("curriculum", {}).get("env_attributes", {}) if isinstance(train_cfg, dict) else {}
    if not bool(cur.get("enabled", False)):
        return {}
    stages = list(cur.get("stages", []))
    if not stages:
        return {}
    step = int(env_steps)
    for st in stages:
        try:
            until = int(st.get("until_global_env_steps", 0))
        except Exception:
            until = 0
        if step < until:
            return dict(st.get("env_params", {}))
    return dict(stages[-1].get("env_params", {}))


def reward_params_for_global_steps(train_cfg: dict[str, Any], env_steps: int) -> dict[str, Any]:
    params = dict(train_cfg.get("reward", {})) if isinstance(train_cfg, dict) else {}
    params.update(stage_env_params_for_steps(train_cfg, env_steps))
    return params


def fixed_target_from_train_cfg(train_cfg: dict[str, Any]) -> dict[str, float]:
    """Return the nominal fixed target used for deterministic eval.

    B95 trains with per-episode randomized command targets, but fixed-target
    probes/eval must stay anchored to the original design point.
    """
    tgt = train_cfg.get("target", {}) if isinstance(train_cfg, dict) else {}
    return {
        "R": float(tgt.get("R", 0.75)),
        "Z": float(tgt.get("Z", 0.0)),
        "Ip": float(tgt.get("Ip", 29779.724)),
    }


def _clamp01(x: Any, default: float = 0.0) -> float:
    try:
        return float(np.clip(float(x), 0.0, 1.0))
    except Exception:
        return float(default)


def _scheduled_fixed_probability(cfg: dict[str, Any], env_steps: int, default: float = 0.0) -> float:
    """Return fixed-target probability from an optional absolute-step schedule."""
    p = _clamp01(cfg.get("fixed_probability", default), default)
    sched = cfg.get("fixed_probability_schedule", None)
    if isinstance(sched, (list, tuple)):
        try:
            pairs = []
            for item in sched:
                if isinstance(item, dict):
                    step = int(item.get("global_env_steps", item.get("step", 0)))
                    prob = _clamp01(item.get("fixed_probability", item.get("probability", p)), p)
                else:
                    step = int(item[0])
                    prob = _clamp01(item[1], p)
                pairs.append((step, prob))
            pairs.sort(key=lambda x: x[0])
            for step, prob in pairs:
                if int(env_steps) >= step:
                    p = prob
        except Exception:
            pass
    return float(p)


def target_randomization_params_for_global_steps(train_cfg: dict[str, Any], env_steps: int) -> dict[str, Any]:
    """Return the active target-randomization / fixed-random mix stage.

    B97 uses the same per-episode command-target injection mechanism, but the
    default training distribution is fixed-core: most episodes use the fixed
    deployment target and a small minority use symmetric local jitter.  This is
    meant to prepare a goal-ready backbone without reintroducing one-sided
    target bias.

    The schedule uses absolute global env-step thresholds when stages are
    provided, so resume runs enter the intended stage immediately.
    """
    cfg = train_cfg.get("target_randomization", {}) if isinstance(train_cfg, dict) else {}
    if not isinstance(cfg, dict) or not bool(cfg.get("enabled", False)):
        return {"enabled": False, "stage_name": "off", "fixed_probability": 1.0}

    out = dict(cfg)
    stages = list(cfg.get("stages", []) or [])
    selected = None
    if stages:
        for st in stages:
            if not isinstance(st, dict):
                continue
            selected = st
            until = st.get("until_global_env_steps", None)
            if until is None or int(env_steps) < int(until):
                break
        if selected is not None:
            for k, v in selected.items():
                if k not in {"name", "until_global_env_steps"}:
                    out[k] = v
            out["stage_name"] = str(selected.get("name", "unnamed"))
            out["until_global_env_steps"] = selected.get("until_global_env_steps", None)
    else:
        out["stage_name"] = str(out.get("stage_name", "no_stage"))

    # Either a stage-level fixed_probability or a global fixed_probability_schedule
    # can be used.  The schedule is applied last so it can override broad defaults.
    out["fixed_probability"] = _scheduled_fixed_probability(out, env_steps, default=float(out.get("fixed_probability", 0.0) or 0.0))
    out["enabled"] = True
    return out

def _sample_scalar_from_range(rng: np.random.Generator, value: Any, fallback: float) -> float:
    try:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            lo, hi = float(value[0]), float(value[1])
            if hi < lo:
                lo, hi = hi, lo
            return float(rng.uniform(lo, hi))
        return float(value)
    except Exception:
        return float(fallback)


def sample_target_from_params(
    rng: np.random.Generator,
    base_target: dict[str, float],
    params: dict[str, Any] | None,
) -> dict[str, float]:
    """Sample one per-episode command target.

    Supported forms per key X in {R,Z,Ip}:
      - "X_range": [absolute_min, absolute_max]
      - "X_delta_range": [delta_min, delta_max] relative to base target
      - "X_delta_abs": d, shorthand for [-d,+d]

    B96/B97 extension:
      - "fixed_probability": with this probability, return the fixed base target
        instead of a random one.  This lets local target jitter act as a
        regularizer while keeping the deployment target prominent in training.
    """
    p = params if isinstance(params, dict) else {}
    enabled = bool(p.get("enabled", False))
    fixed_prob = _clamp01(p.get("fixed_probability", 0.0), 0.0) if enabled else 1.0

    use_fixed = (not enabled) or (rng.random() < fixed_prob)
    if use_fixed:
        out = dict(base_target)
        out["__target_is_fixed"] = True
        out["__target_source"] = "fixed"
        out["__target_fixed_probability"] = float(fixed_prob)
        return out

    out = dict(base_target)
    for key in ("R", "Z", "Ip"):
        base = float(base_target[key])
        if f"{key}_range" in p:
            out[key] = _sample_scalar_from_range(rng, p.get(f"{key}_range"), base)
        elif f"{key}_delta_range" in p:
            delta = _sample_scalar_from_range(rng, p.get(f"{key}_delta_range"), 0.0)
            out[key] = float(base + delta)
        elif f"{key}_delta_abs" in p:
            d = abs(float(p.get(f"{key}_delta_abs", 0.0) or 0.0))
            out[key] = float(base + rng.uniform(-d, d))
    out["__target_is_fixed"] = False
    out["__target_source"] = "random"
    out["__target_fixed_probability"] = float(fixed_prob)
    return out

def apply_target_to_train_config(train_cfg: dict[str, Any], target: dict[str, float]) -> None:
    train_cfg.setdefault("target", {})["R"] = float(target["R"])
    train_cfg.setdefault("target", {})["Z"] = float(target["Z"])
    train_cfg.setdefault("target", {})["Ip"] = float(target["Ip"])


def _try_update_target_dict(obj: Any, target: dict[str, float]) -> None:
    if isinstance(obj, dict):
        obj.setdefault("target", {})["R"] = float(target["R"])
        obj.setdefault("target", {})["Z"] = float(target["Z"])
        obj.setdefault("target", {})["Ip"] = float(target["Ip"])


def apply_target_to_env_object(env: Any, target: dict[str, float]) -> None:
    """Best-effort target injection for the current env instance.

    The native env usually receives target through train_config.  This helper
    also updates common attribute names so B95 remains robust if the env cached
    target values during construction.  Missing attributes are ignored.
    """
    seen: set[int] = set()
    stack: list[Any] = [env]
    for attr in ("unwrapped", "env", "base_env"):
        try:
            x = getattr(env, attr, None)
            if x is not None:
                stack.append(x)
        except Exception:
            pass
    while stack:
        obj = stack.pop()
        if obj is None or id(obj) in seen:
            continue
        seen.add(id(obj))
        for cfg_attr in ("train_config", "train_cfg", "cfg", "config", "env_config"):
            try:
                _try_update_target_dict(getattr(obj, cfg_attr, None), target)
            except Exception:
                pass
        for attr, val in [
            ("target_R", target["R"]), ("target_Z", target["Z"]), ("target_Ip", target["Ip"]),
            ("R_target", target["R"]), ("Z_target", target["Z"]), ("Ip_target", target["Ip"]),
        ]:
            try:
                if hasattr(obj, attr):
                    setattr(obj, attr, float(val))
            except Exception:
                pass
        try:
            tgt_obj = getattr(obj, "target", None)
            if isinstance(tgt_obj, dict):
                tgt_obj.update({"R": float(target["R"]), "Z": float(target["Z"]), "Ip": float(target["Ip"])})
        except Exception:
            pass


def target_info_fields(target: dict[str, float], params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params if isinstance(params, dict) else {}
    is_fixed = bool(target.get("__target_is_fixed", not bool(p.get("enabled", False))))
    fixed_prob = float(target.get("__target_fixed_probability", p.get("fixed_probability", 1.0 if is_fixed else 0.0)) or 0.0)
    return {
        "target_R": float(target["R"]),
        "target_Z": float(target["Z"]),
        "target_Ip": float(target["Ip"]),
        "target_randomization_enabled": bool(p.get("enabled", False)),
        "target_randomization_stage": str(p.get("stage_name", "off")),
        "target_fixed_probability": float(fixed_prob),
        "target_is_fixed": bool(is_fixed),
        "target_source": str(target.get("__target_source", "fixed" if is_fixed else "random")),
    }



def constrained_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (cfg or {}).get("constrained_mpo", {}) if isinstance(cfg, dict) else {}
    return dict(raw or {}) if isinstance(raw, dict) else {}


def cost_configs_from_cfg(cfg: dict[str, Any] | None) -> list[dict[str, Any]]:
    ccfg = constrained_cfg(cfg)
    raw_costs = ccfg.get("costs", [])
    if not raw_costs:
        raw_costs = [
            {"name": "R", "type": "abs_error", "info_key": "R_error", "tol": 0.03, "clip": 20.0},
            {"name": "Z", "type": "abs_error", "info_key": "Z_error", "tol": 0.03, "clip": 20.0},
            {"name": "Ip", "type": "abs_error", "info_key": "Ip_error", "tol": 3500.0, "clip": 20.0},
            {"name": "action", "type": "mean_abs_action", "target": 0.35, "clip": 20.0},
            {"name": "vessel", "type": "info_deadzone", "info_key": "vessel_current_abs_sum_a", "target": 220000.0, "clip": 20.0},
        ]
    out = []
    for c in raw_costs:
        if not isinstance(c, dict):
            continue
        cc = dict(c)
        cc["name"] = sanitize_metric_name(str(cc.get("name", cc.get("info_key", f"cost{len(out)}"))))
        out.append(cc)
    return out


def cost_names_from_cfg(cfg: dict[str, Any] | None) -> list[str]:
    return [sanitize_metric_name(c.get("name", f"cost{i}")) for i, c in enumerate(cost_configs_from_cfg(cfg))]


def compute_constraint_cost_vector(
    info: dict[str, Any] | None,
    action: Any | None,
    cfg: dict[str, Any] | None,
) -> np.ndarray:
    """Compute nonnegative instantaneous constraint-cost vector.

    These are engineering-spec violations, not reward weights.  B99 uses learned
    dual variables to determine their effective pressure on the actor.

    B99.5 adds a ``max_abs_error_late_terminal`` cost type for R/Z/Ip.  It keeps
    the same cost dimensions (R, Z, Ip) while making late-hold and terminal errors
    visible to the duals/actor earlier.  This is deliberately symmetric in the
    sign of the error: it is not a directional hand controller.
    """
    info = dict(info or {})
    try:
        act = np.asarray(action, dtype=np.float32).reshape(-1)
    except Exception:
        act = np.zeros(0, dtype=np.float32)

    def _excess_abs(raw_value: float, tol_value: float, power: float = 1.0) -> float:
        tol_value = max(abs(float(tol_value)), 1.0e-12)
        excess = max(0.0, abs(float(raw_value)) - tol_value) / tol_value
        return float(excess ** max(float(power), 1.0e-12))

    def _late_gate(c: dict[str, Any]) -> float:
        # Prefer the environment's smooth hold ramp when present; also support a
        # time-fraction ramp so the cost works even if hold_weight is absent.
        hold_gate = float(np.clip(info_float(info, "hold_weight", 0.0), 0.0, 1.0))
        tf = float(info_float(info, "time_fraction", 0.0))
        start = float(c.get("late_start_fraction", c.get("late_start_time_fraction", 0.55)) or 0.55)
        ramp = max(float(c.get("late_ramp_fraction", 0.15) or 0.15), 1.0e-12)
        time_gate = float(np.clip((tf - start) / ramp, 0.0, 1.0))
        return float(max(hold_gate, time_gate))

    vals: list[float] = []
    for c in cost_configs_from_cfg(cfg):
        typ = str(c.get("type", "abs_error")).lower()
        val = 0.0
        if typ == "abs_error":
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            raw = abs(info_float(info, key, info_float(info, "terminal_" + key, 0.0)))
            tol = max(abs(float(c.get("tol", c.get("target", 1.0)) or 1.0)), 1.0e-12)
            val = max(0.0, raw - tol) / tol
        elif typ == "squared_abs_error":
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            raw = abs(info_float(info, key, info_float(info, "terminal_" + key, 0.0)))
            tol = max(abs(float(c.get("tol", c.get("target", 1.0)) or 1.0)), 1.0e-12)
            val = (max(0.0, raw - tol) / tol) ** 2
        elif typ in {"max_abs_error_late_terminal", "late_terminal_abs_error", "abs_error_max_late_terminal"}:
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            base_tol = float(c.get("tol", c.get("target", 1.0)) or 1.0)
            base_power = float(c.get("power", 1.0) or 1.0)
            current_raw = info_float(info, key, 0.0)
            base_val = _excess_abs(current_raw, base_tol, base_power)

            late_tol = float(c.get("late_tol", base_tol) or base_tol)
            late_power = float(c.get("late_power", base_power) or base_power)
            late_multiplier = float(c.get("late_multiplier", 1.0) or 1.0)
            late_val = late_multiplier * _late_gate(c) * _excess_abs(current_raw, late_tol, late_power)

            term_key = str(c.get("terminal_info_key", "terminal_" + key))
            terminal_active = info_float(info, "terminal_time_ms", 0.0) > 0.0
            terminal_val = 0.0
            if terminal_active:
                terminal_tol = float(c.get("terminal_tol", late_tol) or late_tol)
                terminal_power = float(c.get("terminal_power", late_power) or late_power)
                terminal_multiplier = float(c.get("terminal_multiplier", late_multiplier) or late_multiplier)
                terminal_raw = info_float(info, term_key, current_raw)
                terminal_val = terminal_multiplier * _excess_abs(terminal_raw, terminal_tol, terminal_power)

            combine = str(c.get("combine", "max")).lower()
            if combine in {"sum", "add"}:
                val = base_val + late_val + terminal_val
            else:
                val = max(base_val, late_val, terminal_val)
        elif typ == "mean_abs_action":
            mean_abs = float(np.mean(np.abs(act))) if act.size else 0.0
            target = max(abs(float(c.get("target", 0.35) or 0.35)), 1.0e-12)
            val = max(0.0, mean_abs - target) / target
        elif typ == "max_abs_action":
            max_abs = float(np.max(np.abs(act))) if act.size else 0.0
            target = max(abs(float(c.get("target", 0.75) or 0.75)), 1.0e-12)
            val = max(0.0, max_abs - target) / target
        elif typ == "info_deadzone":
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            raw = abs(info_float(info, key, 0.0))
            target = max(abs(float(c.get("target", 1.0) or 1.0)), 1.0e-12)
            val = max(0.0, raw - target) / target
        elif typ == "info_abs_scaled":
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            scale = max(abs(float(c.get("scale", 1.0) or 1.0)), 1.0e-12)
            val = abs(info_float(info, key, 0.0)) / scale
        else:
            key = str(c.get("info_key", c.get("key", c.get("name", ""))))
            scale = max(abs(float(c.get("scale", 1.0) or 1.0)), 1.0e-12)
            val = max(0.0, info_float(info, key, 0.0)) / scale
        clip = c.get("clip", None)
        if clip is not None:
            val = min(float(val), float(clip))
        vals.append(float(val))
    return np.asarray(vals, dtype=np.float32)

def goal_conditioning_cfg(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Return goal-conditioning config.

    B98 explicitly appends command-target features to the deployable observation.
    This is different from previous B95/B97 target randomization, where the actor
    could only infer command changes indirectly through error terms.  The default
    features are small normalized deltas around the fixed deployment target.
    """
    if not isinstance(cfg, dict):
        return {}
    raw = cfg.get("goal_conditioning", None)
    if raw is None:
        raw = cfg.get("model", {}).get("goal_conditioning", None)
    return dict(raw or {}) if isinstance(raw, dict) else {}


def goal_conditioning_enabled(cfg: dict[str, Any] | None) -> bool:
    gc = goal_conditioning_cfg(cfg)
    return bool(gc.get("enabled", False)) and bool(gc.get("append_to_observation", True))


def goal_feature_names_from_cfg(cfg: dict[str, Any] | None) -> list[str]:
    gc = goal_conditioning_cfg(cfg)
    if not goal_conditioning_enabled(cfg):
        return []
    feats = gc.get("features", None)
    if not feats:
        feats = ["target_R_delta_norm", "target_Z_delta_norm", "target_Ip_delta_norm"]
    return [str(x) for x in feats]


def goal_feature_dim_from_cfg(cfg: dict[str, Any] | None) -> int:
    return len(goal_feature_names_from_cfg(cfg))


def goal_feature_scales_from_cfg(cfg: dict[str, Any] | None) -> dict[str, float]:
    gc = goal_conditioning_cfg(cfg)
    scales = dict(gc.get("scales", {}) or {})
    return {
        "R_scale_m": float(scales.get("R_scale_m", gc.get("R_scale_m", 0.05))),
        "Z_scale_m": float(scales.get("Z_scale_m", gc.get("Z_scale_m", 0.05))),
        "Ip_scale_a": float(scales.get("Ip_scale_a", gc.get("Ip_scale_a", 3000.0))),
    }


def goal_features_for_target(
    target: dict[str, float],
    base_target: dict[str, float],
    cfg: dict[str, Any] | None,
) -> np.ndarray:
    names = goal_feature_names_from_cfg(cfg)
    if not names:
        return np.zeros(0, dtype=np.float32)
    sc = goal_feature_scales_from_cfg(cfg)
    r_scale = max(abs(float(sc.get("R_scale_m", 0.05))), 1.0e-12)
    z_scale = max(abs(float(sc.get("Z_scale_m", 0.05))), 1.0e-12)
    ip_scale = max(abs(float(sc.get("Ip_scale_a", 3000.0))), 1.0e-12)
    vals = {
        "target_R_delta_norm": (float(target["R"]) - float(base_target["R"])) / r_scale,
        "target_Z_delta_norm": (float(target["Z"]) - float(base_target["Z"])) / z_scale,
        "target_Z_norm": float(target["Z"]) / z_scale,
        "target_Ip_delta_norm": (float(target["Ip"]) - float(base_target["Ip"])) / ip_scale,
        "target_R_norm": (float(target["R"]) - 0.75) / r_scale,
        "target_Ip_norm": (float(target["Ip"]) - 29779.724) / ip_scale,
        "target_is_fixed": 1.0 if bool(target.get("__target_is_fixed", False)) else 0.0,
        "target_source_random": 0.0 if bool(target.get("__target_is_fixed", False)) else 1.0,
    }
    return np.asarray([float(vals.get(name, 0.0)) for name in names], dtype=np.float32)


def augment_observation_with_goal(
    obs: Any,
    target: dict[str, float],
    base_target: dict[str, float],
    cfg: dict[str, Any] | None,
) -> np.ndarray:
    arr = np.asarray(obs, dtype=np.float32).reshape(-1)
    feats = goal_features_for_target(target, base_target, cfg)
    if feats.size <= 0:
        return arr
    return np.concatenate([arr, feats.astype(np.float32)], axis=0).astype(np.float32)


def add_goal_conditioning_info_fields(
    out: dict[str, Any],
    target: dict[str, float],
    base_target: dict[str, float],
    cfg: dict[str, Any] | None,
    prefix: str = "goal",
) -> None:
    feats = goal_features_for_target(target, base_target, cfg)
    names = goal_feature_names_from_cfg(cfg)
    out[f"{prefix}_conditioning_enabled"] = bool(goal_conditioning_enabled(cfg))
    out[f"{prefix}_feature_dim"] = int(len(names))
    for name, val in zip(names, feats.tolist()):
        out[f"{prefix}_feature/{sanitize_metric_name(name)}"] = float(val)


def _copy_overlapping_(dst: torch.Tensor, src: torch.Tensor) -> torch.Tensor:
    out = dst.clone()
    slices = tuple(slice(0, min(int(a), int(b))) for a, b in zip(out.shape, src.shape))
    if len(slices) == out.ndim and out.ndim == src.ndim:
        out[slices] = src[slices].to(dtype=out.dtype, device=out.device)
    return out


def adapt_actor_state_for_obs_dim(
    actor: RecurrentGaussianActor,
    saved_state: dict[str, torch.Tensor],
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Adapt actor state when B98 appends goal features to the observation.

    Only the GRU input weight changes shape.  Existing observation columns are
    copied exactly, while new goal-feature columns keep the freshly initialized
    weights, making the resume checkpoint-compatible but initially behavior-close
    to the old fixed-target policy.
    """
    current = actor.state_dict()
    out = {k: v.clone() for k, v in current.items()}
    adapted: list[str] = []
    skipped: list[str] = []
    for k, v in saved_state.items():
        if k not in out:
            skipped.append(k)
            continue
        if tuple(out[k].shape) == tuple(v.shape):
            out[k] = v.to(dtype=out[k].dtype)
        elif k == "gru.weight_ih_l0" and out[k].ndim == 2 and v.ndim == 2 and out[k].shape[0] == v.shape[0] and out[k].shape[1] >= v.shape[1]:
            out[k][:, : v.shape[1]] = v.to(dtype=out[k].dtype)
            adapted.append(k)
        else:
            skipped.append(k)
    return out, {"adapted": adapted, "skipped": skipped}


def adapt_critic_state_for_obs_dim(
    critic: RecurrentQCritic,
    saved_state: dict[str, torch.Tensor],
    *,
    old_obs_dim: int,
    new_obs_dim: int,
    priv_dim: int,
    action_dim: int,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Adapt critic GRU input weights for obs_dim expansion.

    Critic input layout is [obs, privileged, action].  B98 inserts goal features
    at the end of obs, so privileged/action columns shift right by goal_dim.
    """
    current = critic.state_dict()
    out = {k: v.clone() for k, v in current.items()}
    adapted: list[str] = []
    skipped: list[str] = []
    goal_dim = int(new_obs_dim) - int(old_obs_dim)
    for k, v in saved_state.items():
        if k not in out:
            skipped.append(k)
            continue
        if tuple(out[k].shape) == tuple(v.shape):
            out[k] = v.to(dtype=out[k].dtype)
        elif k == "gru.weight_ih_l0" and out[k].ndim == 2 and v.ndim == 2 and out[k].shape[0] == v.shape[0] and goal_dim >= 0:
            new_w = out[k]
            old_w = v.to(dtype=new_w.dtype)
            old_tail = int(priv_dim) + int(action_dim)
            if old_w.shape[1] == int(old_obs_dim) + old_tail and new_w.shape[1] == int(new_obs_dim) + old_tail:
                new_w[:, :old_obs_dim] = old_w[:, :old_obs_dim]
                new_w[:, new_obs_dim:new_obs_dim + old_tail] = old_w[:, old_obs_dim:old_obs_dim + old_tail]
                adapted.append(k)
            else:
                new_w = _copy_overlapping_(new_w, old_w)
                adapted.append(k + "_overlap")
            out[k] = new_w
        else:
            skipped.append(k)
    return out, {"adapted": adapted, "skipped": skipped}


def info_float(info: dict[str, Any] | None, key: str, default: float = 0.0) -> float:
    try:
        if info is None:
            return float(default)
        return float(info.get(key, default))
    except Exception:
        return float(default)


def mode_coeff_lookup(mode_names: list[str] | None, mode_coeff: Any | None) -> dict[str, float]:
    """Return sanitized mode coefficient lookup for reward shaping diagnostics."""
    if mode_names is None or mode_coeff is None:
        return {}
    try:
        arr = np.asarray(mode_coeff, dtype=np.float64).reshape(-1)
    except Exception:
        return {}
    out: dict[str, float] = {}
    for i, raw_name in enumerate(list(mode_names)):
        if i >= arr.size:
            break
        out[sanitize_metric_name(str(raw_name))] = float(arr[i])
    return out


def mode_name_to_index_map(mode_names: list[str] | tuple[str, ...] | None) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, name in enumerate(list(mode_names or [])):
        out[sanitize_metric_name(str(name))] = int(i)
        out[str(name)] = int(i)
    return out


def build_mode_weight_vector(
    mode_names: list[str] | tuple[str, ...] | None,
    raw: Any,
    *,
    default: float = 0.0,
    device: torch.device | str | None = None,
) -> torch.Tensor:
    names = list(mode_names or [])
    vec = torch.full((len(names),), float(default), dtype=torch.float32, device=device)
    if not names or raw is None:
        return vec
    if isinstance(raw, dict):
        idx = mode_name_to_index_map(names)
        for k, v in raw.items():
            key = sanitize_metric_name(str(k))
            if key in idx:
                vec[idx[key]] = float(v)
            elif str(k) in idx:
                vec[idx[str(k)]] = float(v)
    elif isinstance(raw, (list, tuple)):
        if len(raw) != len(names):
            raise ValueError(f"mode weight list must have length {len(names)}, got {len(raw)}")
        vec = torch.tensor([float(x) for x in raw], dtype=torch.float32, device=device)
    else:
        val = float(raw)
        if len(names) > 0:
            vec.fill_(val)
    return vec




def build_action_pair_indices(
    action_names: list[str] | tuple[str, ...] | None,
    raw_pairs: Any,
    *,
    default_pairs: list[tuple[str, str]] | None = None,
) -> list[tuple[int, int, str]]:
    """Resolve action-name pairs to index pairs for actor-side diagnostics/penalties.

    Accepts pairs as either coil-name strings (recommended) or integer indices.  Names are
    sanitized in the same way as CSV metric names, so ``PF2U`` and ``PF2U `` are safe.
    Returns tuples ``(i, j, label)`` where label is safe for metric keys.
    """
    names = [sanitize_metric_name(x) for x in list(action_names or [])]
    idx = {name: i for i, name in enumerate(names)}
    pairs = raw_pairs
    if pairs is None:
        pairs = default_pairs or []
    out: list[tuple[int, int, str]] = []
    for pair in list(pairs or []):
        try:
            if isinstance(pair, dict):
                a = pair.get("u", pair.get("upper", pair.get("a", pair.get("left"))))
                b = pair.get("l", pair.get("lower", pair.get("b", pair.get("right"))))
                label = pair.get("name", None)
            else:
                a, b = pair[0], pair[1]
                label = pair[2] if len(pair) > 2 else None
            if isinstance(a, int) and isinstance(b, int):
                ia, ib = int(a), int(b)
                if ia < 0 or ib < 0 or ia >= len(names) or ib >= len(names):
                    continue
                la, lb = names[ia], names[ib]
            else:
                la = sanitize_metric_name(str(a))
                lb = sanitize_metric_name(str(b))
                if la not in idx or lb not in idx:
                    continue
                ia, ib = idx[la], idx[lb]
            if label is None:
                label = f"{la}_minus_{lb}"
            out.append((ia, ib, sanitize_metric_name(str(label))))
        except Exception:
            continue
    return out

def apply_extra_reward_shaping(
    reward: float,
    info: dict[str, Any] | None,
    reward_params: dict[str, Any] | None,
    *,
    prev_info: dict[str, Any] | None = None,
    mode_names: list[str] | None = None,
    mode_coeff: Any | None = None,
) -> tuple[float, dict[str, float]]:
    """Apply wrapper-side reward terms that are not guaranteed in older env code.

    B90 added one-sided positive-Z suppression. B91 added a stronger one-sided
    negative-R corridor and gated the Z penalty when R was already too inward.

    B92 keeps those useful terms and adds two missing pieces exposed by B91:
    (1) a signed progress term that rewards moving negative R_error back toward 0,
        rather than merely penalizing the final inward offset;
    (2) optional direct penalties on selected physics-mode coefficients, because
        B91 reduced common-mode matrix scales but the actor simply drove the
        corresponding coefficients close to saturation.
    """
    rp = reward_params or {}
    extra_cfg = rp.get("extra_reward_shaping", {}) if isinstance(rp.get("extra_reward_shaping", {}), dict) else {}
    if extra_cfg and not bool(extra_cfg.get("enabled", True)):
        return float(reward), {}

    shaped = float(reward)
    out: dict[str, float] = {}
    r_err = info_float(info, "R_error", info_float(info, "terminal_R_error", 0.0))
    z_err = info_float(info, "Z_error", info_float(info, "terminal_Z_error", 0.0))
    prev_r_err = info_float(prev_info, "R_error", info_float(prev_info, "terminal_R_error", r_err))

    # B91/B92: strong one-sided penalty for excessive inward radial drift.
    w_r_neg = float(rp.get("w_r_negative_bias_strong", 0.0) or 0.0)
    if w_r_neg > 0.0:
        deadband = float(rp.get("r_neg_deadband_m", 0.10) or 0.0)
        ref = max(float(rp.get("r_neg_ref_m", 0.05) or 0.05), 1.0e-12)
        power = float(rp.get("r_neg_power", 2.0) or 2.0)
        r_neg = max(0.0, -r_err - deadband)
        penalty = w_r_neg * (r_neg / ref) ** power
        shaped -= penalty
        out["extra_r_negative_bias_penalty"] = float(penalty)
        out["extra_r_negative_bias_active"] = float(r_neg > 0.0)
        out["extra_r_negative_bias_margin_m"] = float(r_neg)

    # B92: signed progress for negative R.  If R_error is already too negative,
    # reward steps that increase R_error toward zero and penalize steps that move
    # further inward. This helps escape the B91 plateau around R_error=-0.17 m.
    w_r_prog = float(rp.get("w_r_negative_progress", 0.0) or 0.0)
    if w_r_prog > 0.0:
        enable_m = float(rp.get("r_negative_progress_enable_m", -0.08) or -0.08)
        ref = max(float(rp.get("r_negative_progress_ref_m", 0.03) or 0.03), 1.0e-12)
        clip = float(rp.get("r_negative_progress_clip", 2.5) or 2.5)
        active = (r_err < enable_m) or (prev_r_err < enable_m)
        progress_m = r_err - prev_r_err  # positive means R_error moved toward zero.
        progress_norm = float(np.clip(progress_m / ref, -clip, clip)) if active else 0.0
        bonus = w_r_prog * progress_norm
        shaped += bonus
        out["extra_r_negative_progress_bonus"] = float(bonus)
        out["extra_r_negative_progress_m"] = float(progress_m)
        out["extra_r_negative_progress_active"] = float(bool(active))

    # B91: positive-Z penalty remains useful, but it should stop fighting the
    # radial corridor once R is already too negative.
    w_pos_base = float(rp.get("w_z_positive_bias", 0.0) or 0.0)
    w_pos_eff = w_pos_base
    gate_threshold = rp.get("z_pos_gate_r_threshold_m", None)
    if gate_threshold is not None and r_err < float(gate_threshold):
        w_pos_eff *= float(rp.get("z_pos_gate_multiplier", 1.0) or 1.0)
    out["extra_z_positive_bias_weight_effective"] = float(w_pos_eff)

    if w_pos_eff > 0.0:
        deadband = float(rp.get("z_pos_deadband_m", 0.03) or 0.0)
        ref = max(float(rp.get("z_pos_ref_m", 0.05) or 0.05), 1.0e-12)
        power = float(rp.get("z_pos_power", 2.0) or 2.0)
        z_pos = max(0.0, z_err - deadband)
        penalty = w_pos_eff * (z_pos / ref) ** power
        shaped -= penalty
        out["extra_z_positive_bias_penalty"] = float(penalty)
        out["extra_z_positive_bias_active"] = float(z_pos > 0.0)

    # B92: direct common-mode coefficient penalties.  These are optional and only
    # applied when mode coefficients are available from the actor diagnostics.
    coeffs = mode_coeff_lookup(mode_names, mode_coeff)
    common_names_raw = rp.get("common_mode_coeff_names", ["outer_pf_common_shape", "cs_common_flux"])
    if isinstance(common_names_raw, str):
        common_names = [common_names_raw]
    else:
        common_names = list(common_names_raw or [])
    common_names = [sanitize_metric_name(str(x)) for x in common_names]
    selected = [coeffs[name] for name in common_names if name in coeffs]
    if selected:
        vals = np.asarray(selected, dtype=np.float64)
        l2 = float(np.mean(vals ** 2))
        w_l2 = float(rp.get("w_common_mode_coeff_l2", 0.0) or 0.0)
        if w_l2 > 0.0:
            penalty = w_l2 * l2
            shaped -= penalty
            out["extra_common_mode_coeff_l2_penalty"] = float(penalty)
        soft_limit = float(rp.get("common_mode_coeff_soft_limit", 1.0) or 1.0)
        w_sat = float(rp.get("w_common_mode_coeff_saturation", 0.0) or 0.0)
        sat_excess = np.maximum(0.0, np.abs(vals) - soft_limit)
        sat = float(np.mean(sat_excess ** 2))
        if w_sat > 0.0:
            penalty = w_sat * sat
            shaped -= penalty
            out["extra_common_mode_coeff_saturation_penalty"] = float(penalty)
        out["extra_common_mode_coeff_abs_mean"] = float(np.mean(np.abs(vals)))
        out["extra_common_mode_coeff_abs_max"] = float(np.max(np.abs(vals)))

    return float(shaped), out

def write_dynamic_csv(csv_path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp_path, csv_path)


def actor_pre_tanh_step(actor: RecurrentGaussianActor, obs: torch.Tensor, hidden: torch.Tensor | None, *, deterministic: bool):
    if obs.ndim == 1:
        obs_seq = obs.view(1, 1, -1)
    elif obs.ndim == 2:
        obs_seq = obs.unsqueeze(1)
    else:
        obs_seq = obs
    dist, mean, _log_std, h = actor.distribution(obs_seq, hidden)
    pre_tanh = mean if deterministic else dist.rsample()
    comps = actor.action_components_from_pre_tanh(pre_tanh)
    return pre_tanh, comps, h


def add_actor_component_diagnostics(
    out: dict[str, Any],
    *,
    prefix: str,
    actor: RecurrentGaussianActor,
    action_sum: np.ndarray | None,
    action_abs_sum: np.ndarray | None,
    raw_sum: np.ndarray | None,
    raw_abs_sum: np.ndarray | None,
    physics_sum: np.ndarray | None,
    physics_abs_sum: np.ndarray | None,
    mode_sum: np.ndarray | None,
    mode_abs_sum: np.ndarray | None,
    n: int,
    coil_names: list[str],
) -> None:
    if n <= 0 or action_sum is None:
        return
    denom = float(max(n, 1))
    for i, name in enumerate(coil_names):
        out[f"{prefix}_action_mean/{name}"] = float(action_sum[i] / denom)
        out[f"{prefix}_action_abs_mean/{name}"] = float(action_abs_sum[i] / denom)
        if raw_sum is not None:
            out[f"{prefix}_raw_action_mean/{name}"] = float(raw_sum[i] / denom)
            out[f"{prefix}_raw_action_abs_mean/{name}"] = float(raw_abs_sum[i] / denom)
        if physics_sum is not None:
            out[f"{prefix}_physics_action_mean/{name}"] = float(physics_sum[i] / denom)
            out[f"{prefix}_physics_action_abs_mean/{name}"] = float(physics_abs_sum[i] / denom)
    names = [sanitize_metric_name(x) for x in getattr(actor, "physics_mode_names", [])]
    if mode_sum is not None and mode_sum.size > 0:
        for i, name in enumerate(names):
            out[f"{prefix}_mode_coeff_mean/{name}"] = float(mode_sum[i] / denom)
            out[f"{prefix}_mode_coeff_abs_mean/{name}"] = float(mode_abs_sum[i] / denom)

def bounded_policy_loss(
    loss: torch.Tensor,
    clip_range: Any | None = None,
    lower: float | None = None,
    upper: float | None = None,
) -> torch.Tensor:
    """Asymmetric scalar policy-loss bound for MPO actor updates.

    B85c used a symmetric torch.clamp(policy_loss_raw, -5, 5).  That is
    dangerous for this experiment: when policy_loss_raw stays above +5 the
    clamp has zero gradient and the actor mean is driven toward zero only by
    regularization.  B86 keeps the positive-loss gradient alive by default
    and clips only the aggressive negative direction.

    Backward compatibility: if clip_range is supplied, it is still accepted,
    but B86 configs should use policy_loss_lower_clip / policy_loss_upper_clip.
    Set policy_loss_upper_clip to null to avoid the B85c no-op failure mode.
    """
    if clip_range is not None:
        # Legacy configs.  Preserve old behavior unless explicit lower/upper
        # keys are also supplied.
        if lower is None:
            lower = float(clip_range[0])
        if upper is None and len(clip_range) > 1 and clip_range[1] is not None:
            upper = float(clip_range[1])
    out = loss
    if lower is not None:
        lo = torch.as_tensor(float(lower), dtype=loss.dtype, device=loss.device)
        out = torch.maximum(out, lo)
    if upper is not None:
        hi = torch.as_tensor(float(upper), dtype=loss.dtype, device=loss.device)
        out = torch.minimum(out, hi)
    return out



@ray.remote
class MpoRolloutWorker:
    def __init__(self, worker_index: int, cfg: dict[str, Any], actor_state: dict[str, Any] | None = None):
        self.worker_index = int(worker_index)
        self.cfg = cfg
        seed = int(cfg.get("seed", 42)) + 1000 * self.worker_index
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)

        train_cfg = copy.deepcopy(cfg["train_config_resolved"])
        self.train_cfg = train_cfg
        self.reward_params = reward_params_for_global_steps(self.train_cfg, 0)
        self.base_target = fixed_target_from_train_cfg(self.train_cfg)
        self.goal_feature_dim = goal_feature_dim_from_cfg(self.cfg)
        self.goal_feature_names = goal_feature_names_from_cfg(self.cfg)
        self.target_rng = np.random.default_rng(seed + 7919)
        self.target_randomization_params = target_randomization_params_for_global_steps(self.train_cfg, 0)
        self.current_target = sample_target_from_params(
            self.target_rng, self.base_target, self.target_randomization_params
        )
        apply_target_to_train_config(self.train_cfg, self.current_target)
        par = cfg.get("parallel", {})
        env_cfg = {
            "backend": cfg.get("env", {}).get("backend", "native"),
            "train_config": train_cfg,
            "seed": seed,
            "worker_index": self.worker_index,
            "vector_index": 0,
            "num_workers_for_curriculum": int(par.get("num_tsc_workers", 1)),
            "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
        }
        self.env = RllibTscRzipEnv(env_cfg)
        apply_target_to_env_object(self.env, self.current_target)
        self.env_obs_dim = int(np.prod(self.env.observation_space.shape))
        self.obs_dim = int(self.env_obs_dim + self.goal_feature_dim)
        self.action_dim = int(np.prod(self.env.action_space.shape))
        p_cfg = cfg.get("privileged", {})
        self.priv_keys = p_cfg.get("keys")
        self.priv_include_currents = bool(p_cfg.get("include_currents", True))
        self.priv_current_scale_a = float(p_cfg.get("current_scale_a", 1000.0))
        self.priv_clip = float(p_cfg.get("clip", 50.0))
        self.priv_scales = dict(p_cfg.get("scales", {}))
        self.priv_dim = privileged_dim(self.priv_keys, include_currents=self.priv_include_currents)
        m_cfg = cfg.get("model", {})
        self.actor = RecurrentGaussianActor(
            self.obs_dim,
            self.action_dim,
            hidden_size=int(m_cfg.get("actor_gru_hidden", 128)),
            mlp_hiddens=list(m_cfg.get("actor_mlp_hiddens", [256, 256])),
            activation=str(m_cfg.get("activation", "silu")),
            log_std_min=float(m_cfg.get("log_std_min", -5.0)),
            log_std_max=float(m_cfg.get("log_std_max", 1.0)),
            physics_blend=m_cfg.get("physics_blend", None),
        )
        if actor_state is not None:
            self.actor.load_state_dict(actor_state)
        self.actor.eval()
        self.action_scale = float(cfg.get("mpo", {}).get("actor_output_scale_init", 1.0))
        phys_cfg = cfg.get("model", {}).get("physics_blend", {})
        self.physics_blend_alpha = float(phys_cfg.get("alpha_init", phys_cfg.get("alpha", 0.0)))
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)
        self.hidden = self.actor.init_hidden(1)
        raw_obs, self.info = self.env.reset(seed=seed)
        self.info = dict(self.info or {})
        self.info.update(target_info_fields(self.current_target, self.target_randomization_params))
        add_goal_conditioning_info_fields(self.info, self.current_target, self.base_target, self.cfg)
        self.obs = augment_observation_with_goal(raw_obs, self.current_target, self.base_target, self.cfg)
        self.priv = self._priv(self.info)
        self.episode_return = 0.0
        self.episode_len = 0
        self.completed_episodes: list[dict[str, Any]] = []

    def set_target_randomization_params(self, params: dict[str, Any] | None = None) -> None:
        if params is not None:
            self.target_randomization_params = dict(params)

    def _sample_and_apply_episode_target(self) -> dict[str, float]:
        self.current_target = sample_target_from_params(
            self.target_rng, self.base_target, self.target_randomization_params
        )
        apply_target_to_train_config(self.train_cfg, self.current_target)
        apply_target_to_env_object(self.env, self.current_target)
        return self.current_target

    def _reset_env_for_next_episode(self, seed: int | None = None) -> None:
        self._sample_and_apply_episode_target()
        if seed is None:
            raw_obs, self.info = self.env.reset()
        else:
            raw_obs, self.info = self.env.reset(seed=seed)
        self.info = dict(self.info or {})
        self.info.update(target_info_fields(self.current_target, self.target_randomization_params))
        add_goal_conditioning_info_fields(self.info, self.current_target, self.base_target, self.cfg)
        self.obs = augment_observation_with_goal(raw_obs, self.current_target, self.base_target, self.cfg)
        self.priv = self._priv(self.info)
        self.hidden = self.actor.init_hidden(1)
        self.episode_return = 0.0
        self.episode_len = 0

    def _priv(self, info: dict[str, Any] | None) -> np.ndarray:
        return build_privileged_vector(
            info,
            keys=self.priv_keys,
            scales=self.priv_scales,
            include_currents=self.priv_include_currents,
            current_scale_a=self.priv_current_scale_a,
            clip=self.priv_clip,
        )

    def set_reward_params(self, reward_params: dict[str, Any] | None = None) -> None:
        if reward_params is not None:
            self.reward_params = dict(reward_params)

    def set_actor_weights(
        self,
        state: dict[str, Any],
        action_scale: float | None = None,
        physics_blend_alpha: float | None = None,
        reward_params: dict[str, Any] | None = None,
        target_randomization_params: dict[str, Any] | None = None,
    ) -> None:
        self.actor.load_state_dict(state)
        self.actor.eval()
        if action_scale is not None:
            self.action_scale = float(action_scale)
        if physics_blend_alpha is not None:
            self.physics_blend_alpha = float(physics_blend_alpha)
            if hasattr(self.actor, "set_physics_blend_alpha"):
                self.actor.set_physics_blend_alpha(self.physics_blend_alpha)
        self.set_reward_params(reward_params)
        self.set_target_randomization_params(target_randomization_params)

    def set_action_scale(
        self,
        action_scale: float,
        physics_blend_alpha: float | None = None,
        reward_params: dict[str, Any] | None = None,
        target_randomization_params: dict[str, Any] | None = None,
    ) -> None:
        self.action_scale = float(action_scale)
        if physics_blend_alpha is not None:
            self.physics_blend_alpha = float(physics_blend_alpha)
            if hasattr(self.actor, "set_physics_blend_alpha"):
                self.actor.set_physics_blend_alpha(self.physics_blend_alpha)
        self.set_reward_params(reward_params)
        self.set_target_randomization_params(target_randomization_params)

    def rollout(self, fragment_steps: int, deterministic: bool = False) -> dict[str, Any]:
        frag_t0 = time.time()
        obs_l, priv_l, act_l, rew_l, done_l, cost_l, nobs_l, npriv_l, mask_l, info_l = [], [], [], [], [], [], [], [], [], []
        env_steps = 0
        action_abs = []
        env_step_wall_times: list[float] = []
        for _ in range(int(fragment_steps)):
            obs_t = torch.as_tensor(self.obs, dtype=torch.float32)
            prev_info = dict(self.info or {})
            with torch.no_grad():
                _pre_tanh, comps, self.hidden = actor_pre_tanh_step(
                    self.actor, obs_t, self.hidden, deterministic=deterministic
                )
                action_t = comps["blended_action"] * float(self.action_scale)
                mode_t = comps["mode_coeff"]
            action = action_t.cpu().numpy().reshape(-1).astype(np.float32)
            mode_names = [sanitize_metric_name(x) for x in getattr(self.actor, "physics_mode_names", [])]
            mode_coeff = mode_t[:, -1, :].detach().cpu().numpy().reshape(-1) if len(mode_names) > 0 else np.zeros(0)
            step_t0 = time.time()
            next_obs, reward_env, terminated, truncated, info = self.env.step(action)
            env_step_wall_times.append(time.time() - step_t0)
            info = dict(info or {})
            reward, extra_reward_info = apply_extra_reward_shaping(
                float(reward_env), info, self.reward_params,
                prev_info=prev_info, mode_names=mode_names, mode_coeff=mode_coeff,
            )
            info.update(extra_reward_info)
            info["reward_env"] = float(reward_env)
            info["reward_shaped"] = float(reward)
            cost_vec = compute_constraint_cost_vector(info, action, self.cfg)
            for cname, cval in zip(cost_names_from_cfg(self.cfg), cost_vec.tolist()):
                info[f"constraint_cost/{cname}"] = float(cval)
            done = bool(terminated or truncated)
            info.update(target_info_fields(self.current_target, self.target_randomization_params))
            add_goal_conditioning_info_fields(info, self.current_target, self.base_target, self.cfg)
            next_obs_arr = augment_observation_with_goal(next_obs, self.current_target, self.base_target, self.cfg)
            next_priv = self._priv(info)

            obs_l.append(self.obs.copy())
            priv_l.append(self.priv.copy())
            act_l.append(action.copy())
            rew_l.append(float(reward))
            done_l.append(float(done))
            cost_l.append(cost_vec.copy())
            nobs_l.append(next_obs_arr.copy())
            npriv_l.append(next_priv.copy())
            mask_l.append(1.0)
            info_l.append({k: v for k, v in dict(info or {}).items() if isinstance(v, (int, float, bool, str))})
            action_abs.append(float(np.mean(np.abs(action))))

            self.episode_return += float(reward)
            self.episode_len += 1
            env_steps += 1
            self.obs = next_obs_arr
            self.priv = next_priv
            self.info = info

            if done:
                ep = {
                    "episode_return": float(self.episode_return),
                    "episode_len": int(self.episode_len),
                    "hold_success": bool(info.get("hold_success", False)),
                    "quality_success": bool(info.get("quality_success", False)),
                    "time_to_first_reach_step": int(info.get("time_to_first_reach_step", info.get("first_reach_step", -1))),
                    "time_to_stable_hold_step": int(info.get("time_to_stable_hold_step", info.get("first_stable_hold_step", -1))),
                    "terminal_R_error": float(info.get("terminal_R_error", info.get("R_error", 0.0))),
                    "terminal_Z_error": float(info.get("terminal_Z_error", info.get("Z_error", 0.0))),
                    "terminal_Ip_error": float(info.get("terminal_Ip_error", info.get("Ip_error", 0.0))),
                    "mean_abs_action_fragment": float(np.mean(action_abs)) if action_abs else 0.0,
                    "target_R": float(self.current_target.get("R", 0.0)),
                    "target_Z": float(self.current_target.get("Z", 0.0)),
                    "target_Ip": float(self.current_target.get("Ip", 0.0)),
                    "target_is_fixed": bool(self.current_target.get("__target_is_fixed", False)),
                    "target_fixed_probability": float(self.current_target.get("__target_fixed_probability", 0.0)),
                    "target_source_random": float(not bool(self.current_target.get("__target_is_fixed", False))),
                }
                self.completed_episodes.append(ep)
                self._reset_env_for_next_episode()

        episodes = self.completed_episodes
        self.completed_episodes = []

        # Fragment-level diagnostic aggregation.  Keep this small and numeric;
        # strings such as boundary_source are represented by explicit numeric
        # flags (boundary_source_is_gfile) from the environment.
        diag_prefixes = ("boundary_", "runner_timing/", "runtime_only_fast_mode")
        diag_values: dict[str, list[float]] = {}
        for inf in info_l:
            for k, v in inf.items():
                if not any(str(k).startswith(pref) for pref in diag_prefixes):
                    continue
                if isinstance(v, bool):
                    fv = float(v)
                elif isinstance(v, (int, float)) and np.isfinite(float(v)):
                    fv = float(v)
                else:
                    continue
                diag_values.setdefault(str(k), []).append(fv)
        fragment_info_means = {k: float(np.mean(vs)) for k, vs in diag_values.items() if vs}
        fragment_info_maxs = {k: float(np.max(vs)) for k, vs in diag_values.items() if vs}
        return {
            "obs": np.asarray(obs_l, dtype=np.float32),
            "priv": np.asarray(priv_l, dtype=np.float32),
            "action": np.asarray(act_l, dtype=np.float32),
            "reward": np.asarray(rew_l, dtype=np.float32),
            "done": np.asarray(done_l, dtype=np.float32),
            "cost": np.asarray(cost_l, dtype=np.float32),
            "next_obs": np.asarray(nobs_l, dtype=np.float32),
            "next_priv": np.asarray(npriv_l, dtype=np.float32),
            "mask": np.asarray(mask_l, dtype=np.float32),
            "info": info_l,
            "worker_index": self.worker_index,
            "env_steps": int(env_steps),
            "fragment_mean_reward": float(np.mean(rew_l)) if rew_l else 0.0,
            "fragment_mean_abs_action": float(np.mean(action_abs)) if action_abs else 0.0,
            "fragment_wall_s": float(time.time() - frag_t0),
            "env_step_wall_s_mean": float(np.mean(env_step_wall_times)) if env_step_wall_times else 0.0,
            "env_step_wall_s_max": float(np.max(env_step_wall_times)) if env_step_wall_times else 0.0,
            "fragment_info_means": fragment_info_means,
            "fragment_info_maxs": fragment_info_maxs,
            "episodes": episodes,
        }

    def close(self):
        try:
            self.env.close()
        except Exception:
            pass


class MpoLearner:
    def __init__(self, cfg: dict[str, Any], obs_dim: int, priv_dim: int, action_dim: int, device: str):
        self.cfg = cfg
        self.device = torch.device(device)
        m_cfg = cfg.get("model", {})
        mpo_cfg = cfg.get("mpo", {})
        self.actor = RecurrentGaussianActor(
            obs_dim,
            action_dim,
            hidden_size=int(m_cfg.get("actor_gru_hidden", 128)),
            mlp_hiddens=list(m_cfg.get("actor_mlp_hiddens", [256, 256])),
            activation=str(m_cfg.get("activation", "silu")),
            log_std_min=float(m_cfg.get("log_std_min", -5.0)),
            log_std_max=float(m_cfg.get("log_std_max", 1.0)),
            physics_blend=m_cfg.get("physics_blend", None),
        ).to(self.device)
        self.q1 = RecurrentQCritic(
            obs_dim,
            priv_dim,
            action_dim,
            hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
            mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
            activation=str(m_cfg.get("activation", "silu")),
        ).to(self.device)
        self.q2 = RecurrentQCritic(
            obs_dim,
            priv_dim,
            action_dim,
            hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
            mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
            activation=str(m_cfg.get("activation", "silu")),
        ).to(self.device)
        self.tq1 = copy.deepcopy(self.q1).to(self.device)
        self.tq2 = copy.deepcopy(self.q2).to(self.device)
        hard_update(self.tq1, self.q1)
        hard_update(self.tq2, self.q2)

        # B99: constrained goal-conditioned MPO.  The original reward critic is
        # kept as the task/return critic, while each engineering constraint gets
        # a separate cost critic.  Effective tradeoff weights are learned dual
        # variables, not hand-picked scalar reward weights.
        self.cost_names = cost_names_from_cfg(cfg)
        self.cost_dim = int(len(self.cost_names))
        self.cost_q1 = torch.nn.ModuleDict()
        self.cost_q2 = torch.nn.ModuleDict()
        self.tcost_q1 = torch.nn.ModuleDict()
        self.tcost_q2 = torch.nn.ModuleDict()
        for cname in self.cost_names:
            c1 = RecurrentQCritic(
                obs_dim, priv_dim, action_dim,
                hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
                mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
                activation=str(m_cfg.get("activation", "silu")),
            ).to(self.device)
            c2 = RecurrentQCritic(
                obs_dim, priv_dim, action_dim,
                hidden_size=int(m_cfg.get("critic_gru_hidden", 256)),
                mlp_hiddens=list(m_cfg.get("critic_mlp_hiddens", [512, 512])),
                activation=str(m_cfg.get("activation", "silu")),
            ).to(self.device)
            self.cost_q1[cname] = c1
            self.cost_q2[cname] = c2
            self.tcost_q1[cname] = copy.deepcopy(c1).to(self.device)
            self.tcost_q2[cname] = copy.deepcopy(c2).to(self.device)
            hard_update(self.tcost_q1[cname], self.cost_q1[cname])
            hard_update(self.tcost_q2[cname], self.cost_q2[cname])
        self.duals = MultiplicativeDuals(cfg.get("constrained_mpo", {}).get("duals", {}), self.cost_names)
        self.cost_critic_loss_coeff = float(cfg.get("constrained_mpo", {}).get("cost_critic_loss_coeff", 1.0))
        self.cost_actor_coeff = float(cfg.get("constrained_mpo", {}).get("actor_cost_coeff", 1.0))
        c_mpo_cfg = cfg.get("constrained_mpo", {}) if isinstance(cfg.get("constrained_mpo", {}), dict) else {}
        self.cost_target_clip = c_mpo_cfg.get("cost_target_clip", None)
        # B99.1 stability controls: cost values are nonnegative by definition,
        # but unconstrained neural cost critics can predict negative Q-costs.
        # The actor and target-cost bootstrap therefore use a smooth nonnegative
        # transform to avoid rewarding the actor for exploiting negative cost-Q.
        self.cost_q_nonnegative_actor = str(c_mpo_cfg.get("cost_q_nonnegative_actor", "softplus")).lower()
        self.cost_q_nonnegative_target = str(c_mpo_cfg.get("cost_q_nonnegative_target", "softplus")).lower()
        self.dual_update_warmup_env_steps = int(c_mpo_cfg.get("dual_update_warmup_env_steps", 300000) or 0)
        self.dual_update_ramp_env_steps = int(c_mpo_cfg.get("dual_update_ramp_env_steps", 600000) or 0)
        self.dual_actor_warmup_env_steps = int(c_mpo_cfg.get("dual_actor_warmup_env_steps", 300000) or 0)
        self.dual_actor_ramp_env_steps = int(c_mpo_cfg.get("dual_actor_ramp_env_steps", 600000) or 0)
        self.current_env_steps = 0

        self.actor_opt = torch.optim.Adam(self.actor.parameters(), lr=float(mpo_cfg.get("actor_lr", 1e-4)))
        critic_params = list(self.q1.parameters()) + list(self.q2.parameters())
        for m in list(self.cost_q1.values()) + list(self.cost_q2.values()):
            critic_params += list(m.parameters())
        self.critic_opt = torch.optim.Adam(critic_params, lr=float(mpo_cfg.get("critic_lr", 3e-4)))
        self.log_eta = torch.nn.Parameter(torch.tensor(float(np.log(np.exp(float(mpo_cfg.get("eta_init", 1.0))) - 1.0)), device=self.device))
        self.eta_opt = torch.optim.Adam([self.log_eta], lr=float(mpo_cfg.get("eta_lr", 1e-3)))
        self.action_dim = int(action_dim)
        self.coil_names = action_names_from_cfg(cfg, self.action_dim)
        self.gamma = float(mpo_cfg.get("gamma", 0.997))
        self.tau = float(mpo_cfg.get("tau", 0.005))
        self.grad_clip = float(mpo_cfg.get("grad_clip", 10.0))
        self.num_action_samples = int(mpo_cfg.get("num_action_samples", 32))
        self.eta_epsilon = float(mpo_cfg.get("eta_epsilon", 0.1))
        self.eta_min = float(mpo_cfg.get("eta_min", 1.0e-3))
        self.kl_coeff = float(mpo_cfg.get("kl_coeff", 1.0))
        self.kl_target = float(mpo_cfg.get("kl_target", 0.02))
        self.entropy_coeff = float(mpo_cfg.get("entropy_coeff", 0.0))
        self.target_noise = float(mpo_cfg.get("target_policy_noise", 0.0))
        self.target_noise_clip = float(mpo_cfg.get("target_noise_clip", 0.3))

        # B85-stable: damp the two failure modes seen in B85-current:
        #   (1) critic/Q scale growth; (2) deterministic action saturation.
        self.critic_loss_type = str(mpo_cfg.get("critic_loss", "mse")).lower()
        self.huber_delta = float(mpo_cfg.get("huber_delta", 10.0))
        self.reward_scale = float(mpo_cfg.get("reward_scale", 1.0))
        self.reward_clip = mpo_cfg.get("reward_clip", None)
        self.target_q_clip = mpo_cfg.get("target_q_clip", None)
        self.eta_max = mpo_cfg.get("eta_max", None)
        self.actor_action_l2_coeff = float(mpo_cfg.get("actor_action_l2_coeff", 0.0))
        self.actor_action_saturation_coeff = float(mpo_cfg.get("actor_action_saturation_coeff", 0.0))
        self.actor_action_soft_limit = float(mpo_cfg.get("actor_action_soft_limit", 0.75))
        self.e_step_center_q = bool(mpo_cfg.get("e_step_center_q", True))
        self.e_step_normalize_q = bool(mpo_cfg.get("e_step_normalize_q", True))
        self.e_step_q_clip = float(mpo_cfg.get("e_step_q_clip", 8.0))

        # B86 balanced actor controls.  These are intentionally actor-side,
        # not only reward-side: B85-stable pushed actions too high, while B85c
        # clipped positive policy-loss gradients and collapsed deterministic mean
        # actions back to no-op.
        self.actor_update_every = max(1, int(mpo_cfg.get("actor_update_every", 1)))
        self.policy_loss_clip = mpo_cfg.get("policy_loss_clip", None)
        self.policy_loss_lower_clip = mpo_cfg.get("policy_loss_lower_clip", None)
        self.policy_loss_upper_clip = mpo_cfg.get("policy_loss_upper_clip", None)
        self.action_scale_default = float(mpo_cfg.get("actor_output_scale", mpo_cfg.get("actor_output_scale_init", 1.0)))
        self.action_scale_schedule = mpo_cfg.get("actor_output_scale_schedule", None)
        self.action_scale = float(self.action_scale_default)

        # B93 actor-side mode regularization.  B92's reward-side common-mode
        # penalties were visible in rollout diagnostics but did not stop the mode
        # head from saturating.  These terms act directly on the actor loss.
        mode_names = [sanitize_metric_name(x) for x in getattr(self.actor, "physics_mode_names", [])]
        self.actor_mode_coeff_l2_weights = build_mode_weight_vector(
            mode_names, mpo_cfg.get("actor_mode_coeff_l2", None), default=0.0, device=self.device
        )
        sat_cfg = mpo_cfg.get("actor_mode_coeff_saturation", {}) or {}
        if not isinstance(sat_cfg, dict):
            sat_cfg = {"coeff": float(sat_cfg)}
        sat_names = sat_cfg.get("names", mode_names)
        if isinstance(sat_names, str):
            sat_names = [sat_names]
        sat_weight_raw = {name: float(sat_cfg.get("coeff", 0.0) or 0.0) for name in list(sat_names or [])}
        self.actor_mode_coeff_sat_weights = build_mode_weight_vector(
            mode_names, sat_weight_raw, default=0.0, device=self.device
        )
        self.actor_mode_coeff_sat_soft_limit = float(sat_cfg.get("soft_limit", 1.0) or 1.0)

        # B94: actor-side raw PF vertical-difference guard.  B93 successfully
        # limited common-mode coefficients, but the raw branch learned a similar
        # inward-biased PF U/L differential pattern.  This regularizer acts
        # directly on the deterministic raw residual action, optionally only when
        # the normalized observation indicates R_error is already too negative.
        raw_pf_cfg = mpo_cfg.get("actor_raw_pf_vertical_diff_when_r_neg", {}) or {}
        if not isinstance(raw_pf_cfg, dict):
            raw_pf_cfg = {"coeff": float(raw_pf_cfg)}
        self.actor_raw_pf_vertical_diff_coeff = float(raw_pf_cfg.get("coeff", 0.0) or 0.0)
        self.actor_raw_pf_vertical_diff_threshold_m = float(raw_pf_cfg.get("r_threshold_m", -0.10) or -0.10)
        self.actor_raw_pf_vertical_diff_obs_index = int(raw_pf_cfg.get("obs_r_error_index", 0) or 0)
        self.actor_raw_pf_vertical_diff_obs_scale_m = float(raw_pf_cfg.get("obs_r_error_scale_m", 0.05) or 0.05)
        self.actor_raw_pf_vertical_diff_use_r_gate = bool(raw_pf_cfg.get("use_r_gate", True))
        self.actor_raw_pf_vertical_diff_pairs = build_action_pair_indices(
            self.coil_names,
            raw_pf_cfg.get("pairs", None),
            default_pairs=[("PF2U", "PF2L"), ("PF3U", "PF3L"), ("PF4U", "PF4L")],
        )

        phys_cfg = m_cfg.get("physics_blend", {})
        self.physics_blend_alpha_default = float(phys_cfg.get("alpha", phys_cfg.get("alpha_init", 0.0)))
        self.physics_blend_alpha_schedule = phys_cfg.get("alpha_schedule", None)
        self.physics_blend_alpha = float(self.physics_blend_alpha_default)
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

        self.update_count = 0

    def set_env_steps(self, env_steps: int) -> None:
        self.current_env_steps = int(env_steps)
        self.action_scale = piecewise_constant_schedule(
            self.action_scale_schedule, int(env_steps), self.action_scale_default
        )
        self.physics_blend_alpha = piecewise_constant_schedule(
            self.physics_blend_alpha_schedule, int(env_steps), self.physics_blend_alpha_default
        )
        if hasattr(self.actor, "set_physics_blend_alpha"):
            self.actor.set_physics_blend_alpha(self.physics_blend_alpha)

    @staticmethod
    def _ramp01(env_steps: int, warmup: int, ramp: int) -> float:
        if env_steps < warmup:
            return 0.0
        if ramp <= 0:
            return 1.0
        return float(min(1.0, max(0.0, (env_steps - warmup) / float(ramp))))

    def _dual_actor_scale(self) -> float:
        return self._ramp01(self.current_env_steps, self.dual_actor_warmup_env_steps, self.dual_actor_ramp_env_steps)

    def _dual_update_scale(self) -> float:
        return self._ramp01(self.current_env_steps, self.dual_update_warmup_env_steps, self.dual_update_ramp_env_steps)

    def _nonnegative_cost_q(self, x: torch.Tensor, mode: str) -> torch.Tensor:
        mode = (mode or "none").lower()
        if mode in {"softplus", "sp"}:
            return F.softplus(x)
        if mode in {"clamp", "relu"}:
            return torch.clamp(x, min=0.0)
        return x

    def _clamp_eta_(self) -> None:
        if self.eta_max is None:
            return
        eta_max = max(float(self.eta_max), self.eta_min + 1.0e-6)
        # eta = softplus(log_eta) + eta_min; inverse softplus for clamp.
        max_raw = eta_max - self.eta_min
        inv = math.log(math.expm1(max_raw)) if max_raw < 50.0 else max_raw
        with torch.no_grad():
            self.log_eta.clamp_(max=inv)

    def _apply_reward_and_target_scaling(self, reward: torch.Tensor, target_q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        r = reward * self.reward_scale
        if self.reward_clip is not None:
            lo, hi = float(self.reward_clip[0]), float(self.reward_clip[1])
            r = torch.clamp(r, lo, hi)
        tq = target_q
        if self.target_q_clip is not None:
            lo, hi = float(self.target_q_clip[0]), float(self.target_q_clip[1])
            tq = torch.clamp(tq, lo, hi)
        return r, tq

    def _td_loss(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if self.critic_loss_type in {"huber", "smooth_l1", "smoothl1"}:
            try:
                return F.huber_loss(pred, target, reduction="none", delta=self.huber_delta)
            except TypeError:
                return F.smooth_l1_loss(pred, target, reduction="none", beta=self.huber_delta)
        return (pred - target).pow(2)

    def _prepare_e_step_q(self, q_cand: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        q = q_cand.detach()
        if self.e_step_center_q:
            q = q - q.mean(dim=-1, keepdim=True)
        if self.e_step_normalize_q:
            q = q / torch.clamp(q.std(dim=-1, keepdim=True), min=1.0e-3)
        if self.e_step_q_clip > 0.0:
            q = torch.clamp(q, -self.e_step_q_clip, self.e_step_q_clip)
        return q * mask.unsqueeze(-1)

    def actor_state_cpu(self) -> dict[str, Any]:
        return {k: v.detach().cpu() for k, v in self.actor.state_dict().items()}

    def _to_torch(self, batch: dict[str, np.ndarray]) -> dict[str, torch.Tensor]:
        return {k: torch.as_tensor(v, dtype=torch.float32, device=self.device) for k, v in batch.items()}

    def update(self, batch_np: dict[str, np.ndarray]) -> dict[str, float]:
        update_total_t0 = time.time()
        t_stage = update_total_t0
        b = self._to_torch(batch_np)
        obs = b["obs"]
        priv = b["priv"]
        action = b["action"]
        reward = b["reward"]
        done = b["done"]
        cost = b.get("cost", torch.zeros((*reward.shape, 0), dtype=torch.float32, device=self.device))
        if cost.ndim != 3:
            cost = torch.zeros((*reward.shape, 0), dtype=torch.float32, device=self.device)
        if cost.shape[-1] < self.cost_dim:
            pad = torch.zeros((*cost.shape[:-1], self.cost_dim - cost.shape[-1]), dtype=cost.dtype, device=cost.device)
            cost = torch.cat([cost, pad], dim=-1)
        elif cost.shape[-1] > self.cost_dim:
            cost = cost[..., :self.cost_dim]
        next_obs = b["next_obs"]
        next_priv = b["next_priv"]
        mask = b["mask"]
        mask_sum = torch.clamp(mask.sum(), min=1.0)
        timing_to_torch_s = time.time() - t_stage
        t_stage = time.time()

        # Critic update.
        with torch.no_grad():
            next_action, _, _, _, _ = self.actor.sample(next_obs, deterministic=False, action_scale=self.action_scale)
            if self.target_noise > 0.0:
                noise = torch.randn_like(next_action) * self.target_noise
                noise = noise.clamp(-self.target_noise_clip, self.target_noise_clip)
                next_action = (next_action + noise).clamp(-1.0, 1.0)
            target_q = torch.min(self.tq1(next_obs, next_priv, next_action), self.tq2(next_obs, next_priv, next_action))
            scaled_reward, target_q = self._apply_reward_and_target_scaling(reward, target_q)
            y = scaled_reward + self.gamma * (1.0 - done) * target_q
            if self.target_q_clip is not None:
                lo, hi = float(self.target_q_clip[0]), float(self.target_q_clip[1])
                y = torch.clamp(y, lo, hi)
        q1 = self.q1(obs, priv, action)
        q2 = self.q2(obs, priv, action)
        reward_critic_loss = ((self._td_loss(q1, y) + self._td_loss(q2, y)) * mask).sum() / mask_sum
        cost_critic_loss = torch.zeros((), dtype=reward_critic_loss.dtype, device=self.device)
        cost_q_current: list[torch.Tensor] = []
        if self.cost_dim > 0:
            with torch.no_grad():
                for i, cname in enumerate(self.cost_names):
                    tqc_raw = torch.min(self.tcost_q1[cname](next_obs, next_priv, next_action), self.tcost_q2[cname](next_obs, next_priv, next_action))
                    tqc = self._nonnegative_cost_q(tqc_raw, self.cost_q_nonnegative_target)
                    cy = cost[..., i] + self.gamma * (1.0 - done) * tqc
                    if self.cost_target_clip is not None:
                        lo, hi = float(self.cost_target_clip[0]), float(self.cost_target_clip[1])
                        cy = torch.clamp(cy, lo, hi)
                    cq1 = self.cost_q1[cname](obs, priv, action)
                    cq2 = self.cost_q2[cname](obs, priv, action)
                    cost_q_current.append(torch.min(cq1, cq2))
                    cost_critic_loss = cost_critic_loss + ((self._td_loss(cq1, cy) + self._td_loss(cq2, cy)) * mask).sum() / mask_sum
        critic_loss = reward_critic_loss + self.cost_critic_loss_coeff * cost_critic_loss
        self.critic_opt.zero_grad(set_to_none=True)
        critic_loss.backward()
        critic_params = list(self.q1.parameters()) + list(self.q2.parameters())
        for m in list(self.cost_q1.values()) + list(self.cost_q2.values()):
            critic_params += list(m.parameters())
        torch.nn.utils.clip_grad_norm_(critic_params, self.grad_clip)
        self.critic_opt.step()
        timing_critic_s = time.time() - t_stage
        t_stage = time.time()

        # MPO E-step temperature update and M-step actor update.
        with torch.no_grad():
            old_dist, old_mean, old_log_std, _ = self.actor.distribution(obs)
            # Candidate pre-tanh samples: [B,T,K,A]
            B, T, latent_dim = old_mean.shape
            eps = torch.randn(B, T, self.num_action_samples, latent_dim, device=self.device)
            old_std = old_log_std.exp().unsqueeze(2)
            pre_tanh = old_mean.unsqueeze(2) + old_std * eps
            cand_action = self.actor.action_from_pre_tanh(pre_tanh, action_scale=self.action_scale)
            obs_rep = obs.unsqueeze(2).expand(B, T, self.num_action_samples, obs.shape[-1]).permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, obs.shape[-1])
            priv_rep = priv.unsqueeze(2).expand(B, T, self.num_action_samples, priv.shape[-1]).permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, priv.shape[-1])
            action_dim = cand_action.shape[-1]
            act_rep = cand_action.permute(0, 2, 1, 3).reshape(B * self.num_action_samples, T, action_dim)
            q_cand = torch.min(self.q1(obs_rep, priv_rep, act_rep), self.q2(obs_rep, priv_rep, act_rep))
            q_cand = q_cand.reshape(B, self.num_action_samples, T).permute(0, 2, 1)  # [B,T,K]
            q_cand = q_cand * mask.unsqueeze(-1)
        timing_candidate_q_s = time.time() - t_stage
        t_stage = time.time()

        eta = F.softplus(self.log_eta) + self.eta_min
        q_e = self._prepare_e_step_q(q_cand, mask)
        # Dual objective for eta: eta*eps + eta*E[logmeanexp(A/eta)].
        # B85-stable uses centered/normalized candidate advantages A to prevent
        # absolute Q-scale growth from driving eta and actor updates into a saturated policy.
        lse = torch.logsumexp(q_e / eta, dim=-1) - np.log(self.num_action_samples)
        eta_loss = (eta * self.eta_epsilon + eta * ((lse * mask).sum() / mask_sum))
        self.eta_opt.zero_grad(set_to_none=True)
        eta_loss.backward()
        torch.nn.utils.clip_grad_norm_([self.log_eta], self.grad_clip)
        self.eta_opt.step()
        self._clamp_eta_()
        eta_used = (F.softplus(self.log_eta) + self.eta_min).detach()
        timing_eta_s = time.time() - t_stage
        t_stage = time.time()

        with torch.no_grad():
            weights = torch.softmax(q_e / eta_used, dim=-1)  # [B,T,K]
            pre_tanh_detached = pre_tanh.detach()
            old_mean_detached = old_mean.detach()
            old_log_std_detached = old_log_std.detach()

        _, new_mean, new_log_std, _ = self.actor.distribution(obs)
        new_mean_k = new_mean.unsqueeze(2).expand_as(pre_tanh_detached)
        new_log_std_k = new_log_std.unsqueeze(2).expand_as(pre_tanh_detached)
        logp_new = tanh_gaussian_log_prob(pre_tanh_detached, new_mean_k, new_log_std_k)  # [B,T,K]
        policy_loss_raw = -((weights * logp_new).sum(dim=-1) * mask).sum() / mask_sum
        policy_loss_used = bounded_policy_loss(policy_loss_raw, self.policy_loss_clip, self.policy_loss_lower_clip, self.policy_loss_upper_clip)
        kl = gaussian_kl(old_mean_detached, old_log_std_detached, new_mean, new_log_std)
        kl_mean = (kl * mask).sum() / mask_sum
        # Penalize only KL above target, leaving small useful updates alone.
        kl_penalty = self.kl_coeff * torch.relu(kl_mean - self.kl_target).pow(2)
        entropy = (0.5 + 0.5 * np.log(2.0 * np.pi) + new_log_std).sum(dim=-1)
        entropy_mean = (entropy * mask).sum() / mask_sum
        mean_components = self.actor.action_components_from_pre_tanh(new_mean)
        mean_action_unscaled = mean_components["blended_action"]
        mean_action = mean_action_unscaled * self.action_scale
        raw_mean_action = mean_components["raw_action"] * self.action_scale
        phys_mean_action = mean_components["physics_action"] * self.action_scale
        mode_coeff = mean_components["mode_coeff"]
        mode_coeff_raw = mean_components.get("mode_coeff_raw", mode_coeff)
        actor_action_l2 = self.actor_action_l2_coeff * ((mean_action.pow(2).mean(dim=-1) * mask).sum() / mask_sum)
        sat_excess = torch.relu(mean_action.abs() - self.actor_action_soft_limit)
        actor_action_saturation = self.actor_action_saturation_coeff * ((sat_excess.pow(2).mean(dim=-1) * mask).sum() / mask_sum)
        actor_mode_coeff_l2 = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        actor_mode_coeff_saturation = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        if mode_coeff_raw.numel() > 0:
            mask_mode = mask.unsqueeze(-1)
            l2_w = self.actor_mode_coeff_l2_weights.to(dtype=mode_coeff_raw.dtype, device=mode_coeff_raw.device)
            if torch.any(l2_w > 0):
                actor_mode_coeff_l2 = ((mode_coeff_raw.pow(2) * l2_w.view(1, 1, -1)) * mask_mode).sum() / mask_sum
            sat_w = self.actor_mode_coeff_sat_weights.to(dtype=mode_coeff_raw.dtype, device=mode_coeff_raw.device)
            if torch.any(sat_w > 0):
                sat_excess_mode = torch.relu(mode_coeff_raw.abs() - self.actor_mode_coeff_sat_soft_limit)
                actor_mode_coeff_saturation = ((sat_excess_mode.pow(2) * sat_w.view(1, 1, -1)) * mask_mode).sum() / mask_sum

        actor_raw_pf_vertical_diff_penalty = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        actor_raw_pf_vertical_diff_active_frac = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        actor_raw_pf_vertical_diff_mean_sq = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        if self.actor_raw_pf_vertical_diff_coeff > 0.0 and self.actor_raw_pf_vertical_diff_pairs:
            pair_terms = []
            for ia, ib, _label in self.actor_raw_pf_vertical_diff_pairs:
                if ia < raw_mean_action.shape[-1] and ib < raw_mean_action.shape[-1]:
                    # Half-difference keeps the scale comparable to a single coil action.
                    pair_terms.append(0.5 * (raw_mean_action[..., ia] - raw_mean_action[..., ib]))
            if pair_terms:
                pair_stack = torch.stack(pair_terms, dim=-1)
                pair_sq = pair_stack.pow(2).mean(dim=-1)
                gate = mask
                if self.actor_raw_pf_vertical_diff_use_r_gate:
                    ridx = int(self.actor_raw_pf_vertical_diff_obs_index)
                    if 0 <= ridx < obs.shape[-1]:
                        r_err_m = obs[..., ridx] * self.actor_raw_pf_vertical_diff_obs_scale_m
                        gate = gate * (r_err_m < self.actor_raw_pf_vertical_diff_threshold_m).to(dtype=mask.dtype)
                gate_sum = torch.clamp(gate.sum(), min=1.0)
                actor_raw_pf_vertical_diff_mean_sq = (pair_sq * gate).sum() / gate_sum
                actor_raw_pf_vertical_diff_penalty = self.actor_raw_pf_vertical_diff_coeff * actor_raw_pf_vertical_diff_mean_sq
                actor_raw_pf_vertical_diff_active_frac = gate.sum() / mask_sum
        actor_cost_penalty = torch.zeros((), dtype=mean_action.dtype, device=self.device)
        actor_cost_values = torch.zeros((self.cost_dim,), dtype=mean_action.dtype, device=self.device)
        actor_cost_values_raw = torch.zeros((self.cost_dim,), dtype=mean_action.dtype, device=self.device)
        dual_values = self.duals.values_tensor(device=self.device, dtype=mean_action.dtype) if self.cost_dim > 0 else torch.zeros(0, device=self.device)
        dual_actor_scale = float(self._dual_actor_scale())
        if self.cost_dim > 0:
            vals = []
            raw_vals = []
            for i, cname in enumerate(self.cost_names):
                c_q_raw = torch.min(self.cost_q1[cname](obs, priv, mean_action), self.cost_q2[cname](obs, priv, mean_action))
                c_q = self._nonnegative_cost_q(c_q_raw, self.cost_q_nonnegative_actor)
                raw_vals.append((c_q_raw * mask).sum() / mask_sum)
                vals.append((c_q * mask).sum() / mask_sum)
            actor_cost_values_raw = torch.stack(raw_vals)
            actor_cost_values = torch.stack(vals)
            actor_cost_penalty = self.cost_actor_coeff * float(dual_actor_scale) * torch.sum(dual_values * actor_cost_values)

        actor_loss = (
            policy_loss_used
            + kl_penalty
            - self.entropy_coeff * entropy_mean
            + actor_action_l2
            + actor_action_saturation
            + actor_mode_coeff_l2
            + actor_mode_coeff_saturation
            + actor_raw_pf_vertical_diff_penalty
            + actor_cost_penalty
        )
        timing_actor_loss_s = time.time() - t_stage
        t_stage = time.time()
        self.update_count += 1
        actor_update_applied = (self.update_count % self.actor_update_every == 0)
        if actor_update_applied:
            self.actor_opt.zero_grad(set_to_none=True)
            actor_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_clip)
            self.actor_opt.step()
        timing_actor_opt_s = time.time() - t_stage
        t_stage = time.time()

        # Dual variables are updated from observed instantaneous costs.  They are
        # not reward weights; they are learned Lagrange multipliers for the
        # constraint costs specified in the config.
        with torch.no_grad():
            dual_update_scale = float(self._dual_update_scale())
            if self.cost_dim > 0:
                observed_cost_mean = ((cost * mask.unsqueeze(-1)).sum(dim=(0, 1)) / mask_sum).detach()
                if dual_update_scale > 0.0:
                    dual_metrics = self.duals.update(observed_cost_mean, rate_scale=dual_update_scale)
                else:
                    dual_metrics = self.duals.as_metrics(prefix="dual")
            else:
                observed_cost_mean = torch.zeros(0, device=self.device)
                dual_metrics = {}
        timing_dual_s = time.time() - t_stage
        t_stage = time.time()

        soft_update(self.tq1, self.q1, self.tau)
        soft_update(self.tq2, self.q2, self.tau)
        for cname in self.cost_names:
            soft_update(self.tcost_q1[cname], self.cost_q1[cname], self.tau)
            soft_update(self.tcost_q2[cname], self.cost_q2[cname], self.tau)
        timing_target_update_s = time.time() - t_stage
        t_stage = time.time()
        with torch.no_grad():
            q_mean = ((q1 + q2) * 0.5 * mask).sum() / mask_sum
            target_mean = (y * mask).sum() / mask_sum
            diag: dict[str, float] = {}
            coil_names = self.coil_names
            mask_col = mask.unsqueeze(-1)
            for label, tensor in [
                ("actor_action", mean_action),
                ("actor_raw_action", raw_mean_action),
                ("actor_physics_action", phys_mean_action),
            ]:
                signed = (tensor * mask_col).sum(dim=(0, 1)) / mask_sum
                abs_mean = (tensor.abs() * mask_col).sum(dim=(0, 1)) / mask_sum
                for i, cname in enumerate(coil_names[: tensor.shape[-1]]):
                    diag[f"{label}_mean/{cname}"] = float(signed[i].detach().cpu())
                    diag[f"{label}_abs_mean/{cname}"] = float(abs_mean[i].detach().cpu())
            if self.actor_raw_pf_vertical_diff_pairs:
                for ia, ib, label in self.actor_raw_pf_vertical_diff_pairs:
                    if ia < raw_mean_action.shape[-1] and ib < raw_mean_action.shape[-1]:
                        diff = 0.5 * (raw_mean_action[..., ia] - raw_mean_action[..., ib])
                        diag[f"actor_raw_pf_vertical_diff_mean/{label}"] = float(((diff * mask).sum() / mask_sum).detach().cpu())
                        diag[f"actor_raw_pf_vertical_diff_abs_mean/{label}"] = float(((diff.abs() * mask).sum() / mask_sum).detach().cpu())
            if mode_coeff.numel() > 0:
                mode_signed = (mode_coeff * mask_col).sum(dim=(0, 1)) / mask_sum
                mode_abs = (mode_coeff.abs() * mask_col).sum(dim=(0, 1)) / mask_sum
                mode_raw_signed = (mode_coeff_raw * mask_col).sum(dim=(0, 1)) / mask_sum
                mode_raw_abs = (mode_coeff_raw.abs() * mask_col).sum(dim=(0, 1)) / mask_sum
                for i, name in enumerate([sanitize_metric_name(x) for x in self.actor.physics_mode_names]):
                    diag[f"actor_mode_coeff_mean/{name}"] = float(mode_signed[i].detach().cpu())
                    diag[f"actor_mode_coeff_abs_mean/{name}"] = float(mode_abs[i].detach().cpu())
                    diag[f"actor_mode_coeff_raw_mean/{name}"] = float(mode_raw_signed[i].detach().cpu())
                    diag[f"actor_mode_coeff_raw_abs_mean/{name}"] = float(mode_raw_abs[i].detach().cpu())
        return {
            "critic_loss": float(critic_loss.detach().cpu()),
            "reward_critic_loss": float(reward_critic_loss.detach().cpu()),
            "cost_critic_loss": float(cost_critic_loss.detach().cpu()),
            "actor_loss": float(actor_loss.detach().cpu()),
            "actor_cost_penalty": float(actor_cost_penalty.detach().cpu()),
            "dual_actor_scale": float(dual_actor_scale),
            "dual_update_scale": float(dual_update_scale),
            "policy_loss_raw": float(policy_loss_raw.detach().cpu()),
            "policy_loss_used": float(policy_loss_used.detach().cpu()),
            "policy_loss_lower_clip": float(self.policy_loss_lower_clip) if self.policy_loss_lower_clip is not None else float("nan"),
            "policy_loss_upper_clip": float(self.policy_loss_upper_clip) if self.policy_loss_upper_clip is not None else float("nan"),
            "kl_mean": float(kl_mean.detach().cpu()),
            "entropy_mean": float(entropy_mean.detach().cpu()),
            "eta": float((F.softplus(self.log_eta) + self.eta_min).detach().cpu()),
            "eta_loss": float(eta_loss.detach().cpu()),
            "q_mean": float(q_mean.detach().cpu()),
            "target_q_mean": float(target_mean.detach().cpu()),
            "candidate_q_mean": float(((q_cand.detach() * mask.unsqueeze(-1)).sum() / (mask_sum * self.num_action_samples)).cpu()),
            "candidate_adv_mean": float(((q_e.detach() * mask.unsqueeze(-1)).sum() / (mask_sum * self.num_action_samples)).cpu()),
            "candidate_adv_std": float(torch.std(q_e.detach()[mask.unsqueeze(-1).expand_as(q_e) > 0.5]).cpu()) if torch.any(mask > 0.5) else 0.0,
            "actor_action_l2_penalty": float(actor_action_l2.detach().cpu()),
            "actor_action_saturation_penalty": float(actor_action_saturation.detach().cpu()),
            "actor_mode_coeff_l2_penalty": float(actor_mode_coeff_l2.detach().cpu()),
            "actor_mode_coeff_saturation_penalty": float(actor_mode_coeff_saturation.detach().cpu()),
            "actor_mode_coeff_saturation_soft_limit": float(self.actor_mode_coeff_sat_soft_limit),
            "actor_raw_pf_vertical_diff_penalty": float(actor_raw_pf_vertical_diff_penalty.detach().cpu()),
            "actor_raw_pf_vertical_diff_mean_sq": float(actor_raw_pf_vertical_diff_mean_sq.detach().cpu()),
            "actor_raw_pf_vertical_diff_active_frac": float(actor_raw_pf_vertical_diff_active_frac.detach().cpu()),
            "actor_raw_pf_vertical_diff_coeff": float(self.actor_raw_pf_vertical_diff_coeff),
            "actor_mean_abs_action": float(((mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_raw_mean_abs_action": float(((raw_mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_physics_mean_abs_action": float(((phys_mean_action.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()),
            "actor_mode_coeff_mean_abs": float(((mode_coeff.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()) if mode_coeff.numel() > 0 else 0.0,
            "actor_mode_coeff_raw_mean_abs": float(((mode_coeff_raw.abs().mean(dim=-1) * mask).sum() / mask_sum).detach().cpu()) if mode_coeff_raw.numel() > 0 else 0.0,
            "actor_action_scale": float(self.action_scale),
            "actor_physics_blend_alpha": float(self.physics_blend_alpha),
            "actor_update_applied": float(actor_update_applied),
            "timing_update_total_s": float(time.time() - update_total_t0),
            "timing_to_torch_s": float(timing_to_torch_s),
            "timing_critic_s": float(timing_critic_s),
            "timing_candidate_q_s": float(timing_candidate_q_s),
            "timing_eta_s": float(timing_eta_s),
            "timing_actor_loss_s": float(timing_actor_loss_s),
            "timing_actor_opt_s": float(timing_actor_opt_s),
            "timing_dual_s": float(timing_dual_s),
            "timing_target_update_s": float(timing_target_update_s),
            "critic_loss_type": 1.0 if self.critic_loss_type in {"huber", "smooth_l1", "smoothl1"} else 0.0,
            **{f"cost/observed_{name}": float(observed_cost_mean[i].detach().cpu()) for i, name in enumerate(self.cost_names)},
            **{f"cost/actor_q_{name}": float(actor_cost_values[i].detach().cpu()) for i, name in enumerate(self.cost_names)},
            **{f"cost/actor_q_raw_{name}": float(actor_cost_values_raw[i].detach().cpu()) for i, name in enumerate(self.cost_names)},
            **{k: float(v) for k, v in dual_metrics.items()},
            **diag,
        }

    def save_checkpoint(self, path: Path, stats: dict[str, Any]) -> None:
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "actor": self.actor.state_dict(),
            "q1": self.q1.state_dict(),
            "q2": self.q2.state_dict(),
            "tq1": self.tq1.state_dict(),
            "tq2": self.tq2.state_dict(),
            "cost_q1": {k: v.state_dict() for k, v in self.cost_q1.items()},
            "cost_q2": {k: v.state_dict() for k, v in self.cost_q2.items()},
            "tcost_q1": {k: v.state_dict() for k, v in self.tcost_q1.items()},
            "tcost_q2": {k: v.state_dict() for k, v in self.tcost_q2.items()},
            "duals": self.duals.state_dict(),
            "cost_names": list(self.cost_names),
            "actor_opt": self.actor_opt.state_dict(),
            "critic_opt": self.critic_opt.state_dict(),
            "eta_opt": self.eta_opt.state_dict(),
            "log_eta": self.log_eta.detach().cpu(),
            "action_scale": float(self.action_scale),
            "physics_blend_alpha": float(self.physics_blend_alpha),
            "update_count": int(self.update_count),
            "stats": json_safe(stats),
            "config": json_safe(self.cfg),
        }
        torch.save(payload, path / "mpo_checkpoint.pt")
        with open(path / "checkpoint_info.json", "w", encoding="utf-8") as f:
            json.dump(json_safe(stats), f, indent=2, ensure_ascii=False)


def infer_spaces(cfg: dict[str, Any]) -> tuple[int, int, int]:
    """Infer observation/action/privileged dimensions without running TSC.

    B91-hotfix: the previous implementation called ``env.reset()`` here.
    For this TSC backend, reset may launch/prepare a real TSC episode before
    Ray rollout workers are created.  If that serial preflight blocks, the run
    appears to hang after ``Started a local Ray instance`` and no
    ``train_results.jsonl`` is ever written.  The Gym spaces are already
    constructed by ``RllibTscRzipEnv.__init__``, so a reset is unnecessary for
    dimension inference.
    """
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": cfg["train_config_resolved"],
        "seed": int(cfg.get("seed", 42)),
        "worker_index": 0,
        "vector_index": 0,
        "num_workers_for_curriculum": int(cfg.get("parallel", {}).get("num_tsc_workers", 1)),
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    try:
        obs_dim = int(np.prod(env.observation_space.shape)) + goal_feature_dim_from_cfg(cfg)
        action_dim = int(np.prod(env.action_space.shape))
        p_cfg = cfg.get("privileged", {})
        priv_dim = privileged_dim(p_cfg.get("keys"), include_currents=bool(p_cfg.get("include_currents", True)))
        return obs_dim, priv_dim, action_dim
    finally:
        try:
            env.close()
        except Exception:
            pass


def build_run_dirs(cfg: dict[str, Any], config_path: Path) -> tuple[Path, Path, str]:
    stamp = now_stamp()
    run_name = str(cfg.get("run_name", config_path.stem)) + "_" + stamp
    log_root = Path(str(cfg.get("log_root", "ray_results"))).expanduser()
    ckpt_root = Path(str(cfg.get("checkpoint_root", "mpo_checkpoints"))).expanduser()
    run_dir = log_root / run_name
    ckpt_dir = ckpt_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, ckpt_dir, run_name


def summarize_episodes(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    if not episodes:
        return {}
    out = {"episodes_completed": len(episodes)}
    for key in [
        "episode_return",
        "episode_len",
        "hold_success",
        "quality_success",
        "time_to_first_reach_step",
        "time_to_stable_hold_step",
        "terminal_R_error",
        "terminal_Z_error",
        "terminal_Ip_error",
        "mean_abs_action_fragment",
        "target_R",
        "target_Z",
        "target_Ip",
        "target_is_fixed",
        "target_fixed_probability",
        "target_source_random",
    ]:
        vals = []
        for ep in episodes:
            v = ep.get(key)
            if isinstance(v, bool):
                vals.append(float(v))
            elif isinstance(v, (int, float)) and np.isfinite(v):
                vals.append(float(v))
        if vals:
            out[f"episode_{key}_mean"] = float(np.mean(vals))

    # B96/B97: separate fixed-target and jitter/random-target episode diagnostics.
    # The fixed-core curriculum uses local target jitter as a regularizer, so the
    # aggregate episode mean can hide whether fixed deployment episodes improve.
    fixed_eps = [ep for ep in episodes if bool(ep.get("target_is_fixed", False))]
    random_eps = [ep for ep in episodes if not bool(ep.get("target_is_fixed", False))]
    out["episode_fixed_target_count"] = int(len(fixed_eps))
    out["episode_random_target_count"] = int(len(random_eps))
    out["episode_fixed_target_frac"] = float(len(fixed_eps) / max(len(episodes), 1))
    out["episode_random_target_frac"] = float(len(random_eps) / max(len(episodes), 1))

    def add_group(prefix: str, subset: list[dict[str, Any]]) -> None:
        if not subset:
            return
        for gkey in [
            "episode_return",
            "terminal_R_error",
            "terminal_Z_error",
            "terminal_Ip_error",
            "mean_abs_action_fragment",
            "target_R",
            "target_Z",
            "target_Ip",
        ]:
            gvals = []
            for ep in subset:
                v = ep.get(gkey)
                if isinstance(v, bool):
                    gvals.append(float(v))
                elif isinstance(v, (int, float)) and np.isfinite(v):
                    gvals.append(float(v))
            if gvals:
                out[f"episode_{prefix}_{gkey}_mean"] = float(np.mean(gvals))

    add_group("fixed", fixed_eps)
    add_group("random", random_eps)
    return out



def compute_checkpoint_error_score(result: dict[str, Any], cfg: dict[str, Any] | None) -> float:
    """Return a lower-is-better deployment error score for best checkpointing.

    This is a logging/checkpoint selection helper only; it does not affect RL
    rewards, costs, or actor updates.  B99.6 adds it because B99.5 reached its
    best policy around iter36--37 but sparse checkpointing missed that region.
    """
    raw = cfg or {}
    refs = raw.get("error_score_refs", {}) if isinstance(raw.get("error_score_refs", {}), dict) else {}
    weights = raw.get("weights", {}) if isinstance(raw.get("weights", {}), dict) else {}
    r_ref = max(abs(float(refs.get("R_m", 0.05) or 0.05)), 1.0e-12)
    z_ref = max(abs(float(refs.get("Z_m", 0.05) or 0.05)), 1.0e-12)
    ip_ref = max(abs(float(refs.get("Ip_a", 1500.0) or 1500.0)), 1.0e-12)
    act_ref = max(abs(float(refs.get("action_mean_abs", 0.5) or 0.5)), 1.0e-12)
    wr = float(weights.get("R", 1.0) or 1.0)
    wz = float(weights.get("Z", 1.0) or 1.0)
    wi = float(weights.get("Ip", 1.0) or 1.0)
    wa = float(weights.get("action", 0.0) or 0.0)

    r = abs(float(result.get("episode_terminal_R_error_mean", result.get("episode_fixed_terminal_R_error_mean", 0.0)) or 0.0))
    z = abs(float(result.get("episode_terminal_Z_error_mean", result.get("episode_fixed_terminal_Z_error_mean", 0.0)) or 0.0))
    ip = abs(float(result.get("episode_terminal_Ip_error_mean", result.get("episode_fixed_terminal_Ip_error_mean", 0.0)) or 0.0))
    act = abs(float(result.get("episode_mean_abs_action_fragment_mean", result.get("fragment_mean_abs_action", 0.0)) or 0.0))
    score = wr * (r / r_ref) + wz * (z / z_ref) + wi * (ip / ip_ref) + wa * (act / act_ref)
    if not np.isfinite(score):
        return float("inf")
    return float(score)

def force_stage_for_eval(train_cfg: dict[str, Any], stage_name: str | None) -> dict[str, Any]:
    """Return a deterministic eval config for a requested curriculum stage.

    B99 exposed a fragile assumption: online probes asked for stage="final",
    while the new curriculum used descriptive names without "stage3".  B99.1
    treats final/strict as an alias for the last configured stage when no exact
    match exists, so new experiments do not silently lose all eval probes.
    """
    if not stage_name or stage_name == "default":
        return json.loads(json.dumps(train_cfg))
    cfg = json.loads(json.dumps(train_cfg))
    cur = cfg.get("curriculum", {}).get("env_attributes", {})
    stages = list(cur.get("stages", []))
    aliases = {"final": "stage3", "strict": "stage3", "last": "stage3"}
    raw_stage_name = str(stage_name)
    target = aliases.get(raw_stage_name, raw_stage_name)
    match = None
    for st in stages:
        name = str(st.get("name", ""))
        if target == name or name.startswith(target) or target in name:
            match = st
    if match is None and raw_stage_name in {"final", "strict", "last"} and stages:
        match = stages[-1]
    if match is None and stages:
        # Last-resort convenience: integer stage index such as "0", "1", "2".
        try:
            idx = int(raw_stage_name)
            if 0 <= idx < len(stages):
                match = stages[idx]
        except Exception:
            pass
    if match is None:
        available = [str(st.get("name", "")) for st in stages]
        raise ValueError(f"Cannot find eval stage {stage_name!r}; available stages={available}")
    cfg.setdefault("curriculum", {}).setdefault("env_attributes", {})["enabled"] = False
    cfg.setdefault("reward", {}).update(dict(match.get("env_params", {})))
    return cfg


def run_online_policy_probe(
    cfg: dict[str, Any],
    learner: MpoLearner,
    *,
    iteration: int,
    env_steps: int,
    seed: int,
    stage: str,
    deterministic: bool,
    prefix: str,
    target_override: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run one final-stage episode in-process for online diagnosis.

    Deterministic probe is the deployable policy check.  Optional stochastic
    probe helps distinguish "the distribution can sometimes find useful
    actions" from "the deterministic mean is stuck/no-op".
    """
    train_cfg = force_stage_for_eval(cfg["train_config_resolved"], stage)
    if isinstance(train_cfg.get("target_randomization", None), dict):
        train_cfg["target_randomization"]["enabled"] = False
        train_cfg["target_randomization"]["eval_disabled"] = True
    base_target = fixed_target_from_train_cfg(train_cfg)
    probe_target = dict(base_target)
    probe_target["__target_is_fixed"] = True
    probe_target["__target_source"] = "fixed_eval"
    probe_target["__target_fixed_probability"] = 1.0
    if target_override is not None:
        # B98 local-grid eval: probe a nearby commanded target while keeping
        # rollout/eval otherwise deterministic and target-randomization disabled.
        for key in ("R", "Z", "Ip"):
            if key in target_override:
                probe_target[key] = float(target_override[key])
    apply_target_to_train_config(train_cfg, probe_target)
    env_cfg = {
        "backend": cfg.get("env", {}).get("backend", "native"),
        "train_config": train_cfg,
        "seed": int(seed),
        "worker_index": int(cfg.get("parallel", {}).get("num_tsc_workers", 192)) + 10000 + int(iteration) + (0 if deterministic else 5000),
        "vector_index": 0,
        "num_workers_for_curriculum": 1,
        "finite_guard": cfg.get("env", {}).get("finite_guard", {"enabled": True}),
    }
    env = RllibTscRzipEnv(env_cfg)
    raw_obs, info = env.reset(seed=int(seed))
    info = dict(info or {})
    info.update(target_info_fields(probe_target, {"enabled": False, "fixed_probability": 1.0, "stage_name": "eval_fixed"}))
    add_goal_conditioning_info_fields(info, probe_target, base_target, cfg)
    obs = augment_observation_with_goal(raw_obs, probe_target, base_target, cfg)
    hidden = learner.actor.init_hidden(1, device=learner.device)
    total = 0.0
    steps = 0
    action_abs: list[float] = []
    max_abs = 0.0
    last_info = dict(info or {})
    reward_params = dict(train_cfg.get("reward", {}))
    coil_names = action_names_from_cfg(cfg, learner.action_dim)
    action_sum = np.zeros(learner.action_dim, dtype=np.float64)
    action_abs_sum = np.zeros(learner.action_dim, dtype=np.float64)
    raw_sum = np.zeros(learner.action_dim, dtype=np.float64)
    raw_abs_sum = np.zeros(learner.action_dim, dtype=np.float64)
    physics_sum = np.zeros(learner.action_dim, dtype=np.float64)
    physics_abs_sum = np.zeros(learner.action_dim, dtype=np.float64)
    mode_dim = int(getattr(learner.actor, "physics_mode_dim", 0))
    mode_sum = np.zeros(mode_dim, dtype=np.float64)
    mode_abs_sum = np.zeros(mode_dim, dtype=np.float64)
    learner.actor.eval()
    try:
        done = False
        while not done:
            prev_info = dict(last_info or {})
            with torch.no_grad():
                pre_tanh, comps, hidden = actor_pre_tanh_step(
                    learner.actor,
                    torch.as_tensor(obs, dtype=torch.float32, device=learner.device),
                    hidden,
                    deterministic=bool(deterministic),
                )
                action_tensor = comps["blended_action"] * float(learner.action_scale)
                raw_tensor = comps["raw_action"] * float(learner.action_scale)
                physics_tensor = comps["physics_action"] * float(learner.action_scale)
                mode_tensor = comps["mode_coeff"]
            action = action_tensor[:, -1, :].detach().cpu().numpy().reshape(-1).astype(np.float32)
            raw_action = raw_tensor[:, -1, :].detach().cpu().numpy().reshape(-1)
            physics_action = physics_tensor[:, -1, :].detach().cpu().numpy().reshape(-1)
            mode_coeff = mode_tensor[:, -1, :].detach().cpu().numpy().reshape(-1) if mode_dim > 0 else np.zeros(0)
            next_obs, reward_env, terminated, truncated, info = env.step(action)
            info = dict(info or {})
            reward, extra_reward_info = apply_extra_reward_shaping(
                float(reward_env), info, reward_params,
                prev_info=prev_info,
                mode_names=[sanitize_metric_name(x) for x in getattr(learner.actor, "physics_mode_names", [])],
                mode_coeff=mode_coeff,
            )
            info.update(extra_reward_info)
            done = bool(terminated or truncated)
            total += float(reward)
            steps += 1
            action_abs.append(float(np.mean(np.abs(action))))
            max_abs = max(max_abs, float(np.max(np.abs(action))))
            action_sum += action
            action_abs_sum += np.abs(action)
            raw_sum += raw_action
            raw_abs_sum += np.abs(raw_action)
            physics_sum += physics_action
            physics_abs_sum += np.abs(physics_action)
            if mode_dim > 0:
                mode_sum += mode_coeff
                mode_abs_sum += np.abs(mode_coeff)
            info.update(target_info_fields(probe_target, {"enabled": False, "fixed_probability": 1.0, "stage_name": "eval_fixed"}))
            add_goal_conditioning_info_fields(info, probe_target, base_target, cfg)
            obs = augment_observation_with_goal(next_obs, probe_target, base_target, cfg)
            last_info = dict(info or {})
    finally:
        try:
            env.close()
        except Exception:
            pass

    def f(key: str, fallback: str | None = None, default: float = 0.0) -> float:
        try:
            if key in last_info:
                return float(last_info.get(key))
            if fallback is not None:
                return float(last_info.get(fallback, default))
            return float(default)
        except Exception:
            return float(default)

    r_err = f("terminal_R_error", "R_error")
    z_err = f("terminal_Z_error", "Z_error")
    ip_err = f("terminal_Ip_error", "Ip_error")
    mean_action = float(np.mean(action_abs)) if action_abs else 0.0
    esc = cfg.get("early_stop", {})
    score_r_ref = max(float(esc.get("score_r_ref", 0.05)), 1.0e-12)
    score_z_ref = max(float(esc.get("score_z_ref", 0.05)), 1.0e-12)
    score_ip_ref = max(float(esc.get("score_ip_ref", 3000.0)), 1.0e-12)
    score_ip_weight = float(esc.get("score_ip_weight", 0.2))
    score_action_weight = float(esc.get("score_action_weight", 0.2))
    shape_score = abs(r_err) / score_r_ref + abs(z_err) / score_z_ref
    ip_score = abs(ip_err) / score_ip_ref
    relaxed_score = shape_score + score_ip_weight * ip_score + score_action_weight * mean_action

    out = {
        f"{prefix}_iteration": int(iteration),
        f"{prefix}_env_steps": int(env_steps),
        f"{prefix}_return": float(total),
        f"{prefix}_len": int(steps),
        f"{prefix}_hold_success": float(bool(last_info.get("hold_success", False))),
        f"{prefix}_quality_success": float(bool(last_info.get("quality_success", False))),
        f"{prefix}_first_reach": int(last_info.get("time_to_first_reach_step", last_info.get("first_reach_step", -1))),
        f"{prefix}_stable_hold": int(last_info.get("time_to_stable_hold_step", last_info.get("first_stable_hold_step", -1))),
        f"{prefix}_terminal_R_error": float(r_err),
        f"{prefix}_terminal_Z_error": float(z_err),
        f"{prefix}_terminal_Ip_error": float(ip_err),
        f"{prefix}_terminal_velocity_norm": f("terminal_velocity_norm", "velocity_norm"),
        f"{prefix}_mean_abs_action": float(mean_action),
        f"{prefix}_max_abs_action": float(max_abs),
        f"{prefix}_shape_score": float(shape_score),
        f"{prefix}_ip_score": float(ip_score),
        f"{prefix}_relaxed_score": float(relaxed_score),
        f"{prefix}_action_scale": float(learner.action_scale),
        f"{prefix}_physics_blend_alpha": float(getattr(learner, "physics_blend_alpha", 0.0)),
        f"{prefix}_target_R": float(train_cfg.get("target", {}).get("R", 0.75)),
        f"{prefix}_target_Z": float(train_cfg.get("target", {}).get("Z", 0.0)),
        f"{prefix}_target_Ip": float(train_cfg.get("target", {}).get("Ip", 29779.724)),
    }
    add_actor_component_diagnostics(
        out,
        prefix=prefix,
        actor=learner.actor,
        action_sum=action_sum,
        action_abs_sum=action_abs_sum,
        raw_sum=raw_sum,
        raw_abs_sum=raw_abs_sum,
        physics_sum=physics_sum,
        physics_abs_sum=physics_abs_sum,
        mode_sum=mode_sum,
        mode_abs_sum=mode_abs_sum,
        n=steps,
        coil_names=coil_names,
    )
    out[f"{prefix}_extra_z_positive_bias_penalty_last"] = float(last_info.get("extra_z_positive_bias_penalty", 0.0))
    out[f"{prefix}_extra_z_positive_bias_weight_effective_last"] = float(last_info.get("extra_z_positive_bias_weight_effective", 0.0))
    out[f"{prefix}_extra_r_negative_bias_penalty_last"] = float(last_info.get("extra_r_negative_bias_penalty", 0.0))
    out[f"{prefix}_extra_r_negative_progress_bonus_last"] = float(last_info.get("extra_r_negative_progress_bonus", 0.0))
    out[f"{prefix}_extra_r_negative_progress_m_last"] = float(last_info.get("extra_r_negative_progress_m", 0.0))
    out[f"{prefix}_extra_common_mode_coeff_l2_penalty_last"] = float(last_info.get("extra_common_mode_coeff_l2_penalty", 0.0))
    out[f"{prefix}_extra_common_mode_coeff_saturation_penalty_last"] = float(last_info.get("extra_common_mode_coeff_saturation_penalty", 0.0))
    out[f"{prefix}_extra_common_mode_coeff_abs_mean_last"] = float(last_info.get("extra_common_mode_coeff_abs_mean", 0.0))
    return out


def run_online_deterministic_probe(
    cfg: dict[str, Any], learner: MpoLearner, *, iteration: int, env_steps: int, seed: int, stage: str
) -> dict[str, Any]:
    return run_online_policy_probe(
        cfg, learner, iteration=iteration, env_steps=env_steps, seed=seed,
        stage=stage, deterministic=True, prefix="eval_final_det"
    )


def run_online_stochastic_probe(
    cfg: dict[str, Any], learner: MpoLearner, *, iteration: int, env_steps: int, seed: int, stage: str
) -> dict[str, Any]:
    return run_online_policy_probe(
        cfg, learner, iteration=iteration, env_steps=env_steps, seed=seed,
        stage=stage, deterministic=False, prefix="eval_final_stoch"
    )




def _local_grid_values(grid_cfg: dict[str, Any], base_target: dict[str, float]) -> list[dict[str, float]]:
    """Build a small local target grid around the fixed deployment target.

    B97 uses this only for online diagnosis.  It does not change training data.
    The grid checks whether the policy reacts continuously and in the correct
    direction near the fixed target before full variable-target training.
    """
    if not isinstance(grid_cfg, dict) or not bool(grid_cfg.get("enabled", False)):
        return []
    r_vals = list(grid_cfg.get("R_values", []))
    z_vals = list(grid_cfg.get("Z_values", []))
    ip_vals = list(grid_cfg.get("Ip_values", []))
    if not r_vals:
        r_vals = [float(base_target["R"])]
    if not z_vals:
        z_vals = [float(base_target["Z"])]
    if not ip_vals:
        ip_vals = [float(base_target["Ip"])]
    max_points = int(grid_cfg.get("max_points", 27) or 27)
    out: list[dict[str, float]] = []
    for r in r_vals:
        for z in z_vals:
            for ip in ip_vals:
                out.append({"R": float(r), "Z": float(z), "Ip": float(ip)})
                if len(out) >= max_points:
                    return out
    return out


def run_online_local_target_grid_probe(
    cfg: dict[str, Any],
    learner: MpoLearner,
    *,
    iteration: int,
    env_steps: int,
    seed: int,
    stage: str,
) -> dict[str, Any]:
    """Run deterministic fixed-stage probes over a small local target grid.

    Results are summarized to compact metrics so train_results.csv remains
    manageable.  Per-point values are also emitted with stable labels.
    """
    grid_cfg = cfg.get("local_target_grid_probe", {}) or {}
    if not isinstance(grid_cfg, dict) or not bool(grid_cfg.get("enabled", False)):
        return {}
    base_target = fixed_target_from_train_cfg(cfg.get("train_config_resolved", {}))
    targets = _local_grid_values(grid_cfg, base_target)
    if not targets:
        return {}

    r_errs: list[float] = []
    z_errs: list[float] = []
    ip_errs: list[float] = []
    returns: list[float] = []
    shape_scores: list[float] = []
    target_rs: list[float] = []
    target_zs: list[float] = []
    terminal_rs: list[float] = []
    terminal_zs: list[float] = []
    out: dict[str, Any] = {
        "eval_grid_iteration": int(iteration),
        "eval_grid_env_steps": int(env_steps),
        "eval_grid_num_points": int(len(targets)),
    }
    for i, tgt in enumerate(targets):
        pfx = f"eval_grid_p{i:02d}"
        try:
            res = run_online_policy_probe(
                cfg,
                learner,
                iteration=iteration,
                env_steps=env_steps,
                seed=int(seed) + 97 * i,
                stage=stage,
                deterministic=True,
                prefix=pfx,
                target_override=tgt,
            )
            out.update(res)
            r = float(res.get(f"{pfx}_terminal_R_error", np.nan))
            z = float(res.get(f"{pfx}_terminal_Z_error", np.nan))
            ip = float(res.get(f"{pfx}_terminal_Ip_error", np.nan))
            ret = float(res.get(f"{pfx}_return", np.nan))
            sc = float(res.get(f"{pfx}_shape_score", np.nan))
            if np.isfinite(r): r_errs.append(r)
            if np.isfinite(z): z_errs.append(z)
            if np.isfinite(ip): ip_errs.append(ip)
            if np.isfinite(ret): returns.append(ret)
            if np.isfinite(sc): shape_scores.append(sc)
            if np.isfinite(r) and np.isfinite(z):
                target_rs.append(float(tgt["R"]))
                target_zs.append(float(tgt["Z"]))
                terminal_rs.append(float(tgt["R"] + r))
                terminal_zs.append(float(tgt["Z"] + z))
        except Exception as exc:
            out[f"{pfx}_error"] = repr(exc)
            out[f"{pfx}_target_R"] = float(tgt["R"])
            out[f"{pfx}_target_Z"] = float(tgt["Z"])
            out[f"{pfx}_target_Ip"] = float(tgt["Ip"])

    def add_stats(name: str, vals: list[float]) -> None:
        if not vals:
            return
        arr = np.asarray(vals, dtype=np.float64)
        out[f"eval_grid_{name}_mean"] = float(np.mean(arr))
        out[f"eval_grid_{name}_abs_mean"] = float(np.mean(np.abs(arr)))
        out[f"eval_grid_{name}_max_abs"] = float(np.max(np.abs(arr)))
        out[f"eval_grid_{name}_std"] = float(np.std(arr))

    add_stats("R_error", r_errs)
    add_stats("Z_error", z_errs)
    add_stats("Ip_error", ip_errs)
    add_stats("return", returns)
    add_stats("shape_score", shape_scores)

    # B98 goal-readiness diagnostics: finite-difference sensitivity of terminal
    # actual position to commanded target.  A fixed-template policy gives values
    # close to zero; a goal-conditioned local policy should have positive values.
    def _slope(xs: list[float], ys: list[float]) -> float:
        if len(xs) < 2:
            return float("nan")
        x = np.asarray(xs, dtype=np.float64)
        y = np.asarray(ys, dtype=np.float64)
        vx = float(np.var(x))
        if vx <= 1.0e-16:
            return float("nan")
        return float(np.cov(x, y, bias=True)[0, 1] / vx)

    if target_rs and terminal_rs:
        out["eval_grid_R_target_to_terminal_R_slope"] = _slope(target_rs, terminal_rs)
        out["eval_grid_Z_target_to_terminal_Z_slope"] = _slope(target_zs, terminal_zs)
        out["eval_grid_terminal_R_mean"] = float(np.mean(np.asarray(terminal_rs, dtype=np.float64)))
        out["eval_grid_terminal_Z_mean"] = float(np.mean(np.asarray(terminal_zs, dtype=np.float64)))
        out["eval_grid_terminal_R_std"] = float(np.std(np.asarray(terminal_rs, dtype=np.float64)))
        out["eval_grid_terminal_Z_std"] = float(np.std(np.asarray(terminal_zs, dtype=np.float64)))
    return out


def should_early_stop_from_probe(cfg: dict[str, Any], iteration: int, probe: dict[str, Any], bad_probe_count: int) -> tuple[bool, int, str]:
    esc = cfg.get("early_stop", {})
    if not bool(esc.get("enabled", False)):
        return False, bad_probe_count, "disabled"
    if int(iteration) < int(esc.get("min_iteration", 0)):
        return False, bad_probe_count, "below_min_iteration"

    first_reach = int(probe.get("eval_final_det_first_reach", -1))
    hold_success = float(probe.get("eval_final_det_hold_success", 0.0)) > 0.0
    ma = float(probe.get("eval_final_det_mean_abs_action", 0.0))
    r = float(probe.get("eval_final_det_terminal_R_error", 0.0))
    z = float(probe.get("eval_final_det_terminal_Z_error", 0.0))
    ip = float(probe.get("eval_final_det_terminal_Ip_error", 0.0))
    shape_score = float(probe.get("eval_final_det_shape_score", abs(r) / max(float(esc.get("score_r_ref", 0.05)), 1e-12) + abs(z) / max(float(esc.get("score_z_ref", 0.05)), 1e-12)))
    relaxed_score = float(probe.get("eval_final_det_relaxed_score", shape_score + float(esc.get("score_ip_weight", 0.2)) * abs(ip) / max(float(esc.get("score_ip_ref", 3000.0)), 1e-12)))

    bad = False
    reasons: list[str] = []
    if not hold_success:
        if first_reach < 0:
            if bool(esc.get("bad_if_no_first_reach_after_min_iter", False)):
                bad = True
                reasons.append("no_first_reach")
            thr_hi = esc.get("bad_if_no_first_reach_and_mean_action_gt", None)
            if thr_hi is not None and ma > float(thr_hi):
                bad = True
                reasons.append(f"no_first_reach_and_mean_action>{float(thr_hi)}")
            thr_lo = esc.get("bad_if_no_first_reach_and_mean_action_lt", None)
            if thr_lo is not None and ma < float(thr_lo):
                bad = True
                reasons.append(f"no_first_reach_and_mean_action<{float(thr_lo)}")
        z_thr = esc.get("bad_if_z_abs_gt", None)
        if z_thr is not None and abs(z) > float(z_thr):
            bad = True
            reasons.append(f"z_abs>{float(z_thr)}")
        r_neg_thr = esc.get("bad_if_r_error_lt", None)
        if r_neg_thr is not None and r < float(r_neg_thr):
            bad = True
            reasons.append(f"r_error<{float(r_neg_thr)}")
        shape_thr = esc.get("bad_if_shape_score_gt", None)
        if shape_thr is not None and shape_score > float(shape_thr):
            bad = True
            reasons.append(f"shape_score>{float(shape_thr)}")
        relaxed_thr = esc.get("bad_if_relaxed_score_gt", None)
        if relaxed_thr is not None and relaxed_score > float(relaxed_thr):
            bad = True
            reasons.append(f"relaxed_score>{float(relaxed_thr)}")

    if bad:
        bad_probe_count += 1
    else:
        bad_probe_count = 0
    req = int(esc.get("require_consecutive_bad_probes", 2))
    if bad_probe_count >= req:
        return True, bad_probe_count, ";".join(reasons) or "bad_probe"
    return False, bad_probe_count, ";".join(reasons) if bad else "ok"


def main():
    ap = argparse.ArgumentParser(description="Train recurrent MPO for TSC R/Z/Ip control (B88 z-recovery relaxed-Ip-lite compatible).")
    ap.add_argument("--config", required=True, help="MPO training config JSON.")
    ap.add_argument("--override", default=None, help="Optional JSON override.")
    ap.add_argument("--resume", default=None, help="Optional checkpoint directory containing mpo_checkpoint.pt.")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    cfg = load_merged_json(cfg_path, Path(args.override) if args.override else None)
    if args.resume:
        resume_path = Path(args.resume).expanduser()
        ckpt_file = resume_path / "mpo_checkpoint.pt"
        if not ckpt_file.exists():
            raise FileNotFoundError(f"Resume checkpoint not found: {ckpt_file}")
        cfg["resume_checkpoint"] = str(resume_path)

    run_dir, ckpt_dir, run_name = build_run_dirs(cfg, cfg_path)
    cfg["resolved_run_name"] = run_name

    # Resolve placeholders in both the MPO train config and the nested TSC env config.
    # This fixes paths like {TSC_ALL_ROOT}/tsc_simulation/TSC-PCS/gotsc.
    macros = default_macros(run_name)
    os.environ.setdefault("TSC_ALL_ROOT", macros["TSC_ALL_ROOT"])
    train_cfg_path = resolve_path_maybe_relative(expand_macros(str(cfg.get("train_config", "configs/train_b83_fixed_target_1ms.json")), macros))
    train_cfg = expand_macros(load_json(train_cfg_path), macros)
    resolved_cfg_dir = run_dir / "resolved_configs"
    train_cfg = resolve_tsc_config_file(train_cfg, out_dir=resolved_cfg_dir, macros=macros)
    cfg["train_config_resolved"] = train_cfg

    with open(resolved_cfg_dir / "train_config.resolved.json", "w", encoding="utf-8") as f:
        json.dump(json_safe(train_cfg), f, indent=2, ensure_ascii=False)
    with open(run_dir / "mpo_config.resolved.json", "w", encoding="utf-8") as f:
        json.dump(json_safe(cfg), f, indent=2, ensure_ascii=False)

    # Short Ray temp dir to avoid AF_UNIX socket path length issues.
    uid = os.getuid() if hasattr(os, "getuid") else 0
    ray_tmp = Path(os.environ.get("RAY_TMPDIR", f"/tmp/rm{uid}"))
    ray_tmp.mkdir(parents=True, exist_ok=True)
    os.environ["RAY_TMPDIR"] = str(ray_tmp)
    os.environ["TMPDIR"] = str(ray_tmp / "tmp")
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    par = cfg.get("parallel", {})
    ray_num_cpus = int(par.get("ray_num_cpus", min(available_cpu_count(), 200)))
    object_store_memory = int(par.get("object_store_memory", 8 * 1024**3))
    print(f"========== {cfg.get('banner', 'MPO Ray init')} =========", flush=True)
    print(f"run_name         = {run_name}", flush=True)
    print(f"ray_num_cpus     = {ray_num_cpus}", flush=True)
    print(f"RAY_TMPDIR       = {os.environ['RAY_TMPDIR']}", flush=True)
    print(f"num_tsc_workers  = {par.get('num_tsc_workers')}", flush=True)
    print("======================================", flush=True)
    print("[python limits before ray.init]", flush=True)
    print(f"  pid = {os.getpid()}", flush=True)
    print(f"  RLIMIT_NPROC = {resource.getrlimit(resource.RLIMIT_NPROC)}", flush=True)
    print(f"  RLIMIT_NOFILE = {resource.getrlimit(resource.RLIMIT_NOFILE)}", flush=True)
    print("[train_mpo] before ray.init", flush=True)
    ray.init(
        address=par.get("ray_address", None),
        num_cpus=ray_num_cpus if par.get("ray_address", None) is None else None,
        include_dashboard=bool(par.get("include_dashboard", False)),
        ignore_reinit_error=True,
        _temp_dir=str(ray_tmp),
        object_store_memory=object_store_memory,
        runtime_env={"env_vars": ray_worker_env_vars()},
    )

    print("[train_mpo] after ray.init; inferring spaces without env.reset", flush=True)
    obs_dim, priv_dim, action_dim = infer_spaces(cfg)
    print(f"[train_mpo] spaces: obs_dim={obs_dim} priv_dim={priv_dim} action_dim={action_dim}", flush=True)
    device = "cuda" if (torch.cuda.is_available() and int(cfg.get("learner", {}).get("num_gpus", 0)) > 0) else "cpu"
    print(f"[train_mpo] constructing learner on device={device}", flush=True)
    learner = MpoLearner(cfg, obs_dim, priv_dim, action_dim, device=device)
    resume_env_steps = 0
    resume_iteration = 0
    learner.set_env_steps(0)
    if args.resume:
        print(f"[train_mpo] loading resume checkpoint: {Path(args.resume) / 'mpo_checkpoint.pt'}", flush=True)
        payload = torch.load(Path(args.resume) / "mpo_checkpoint.pt", map_location=device)
        saved_actor_state = payload["actor"]
        saved_actor_obs_dim = int(saved_actor_state.get("gru.weight_ih_l0", torch.empty(0, 0)).shape[1])
        new_actor_obs_dim = int(getattr(learner.actor, "obs_dim", obs_dim))
        obs_dim_changed = bool(saved_actor_obs_dim and saved_actor_obs_dim != new_actor_obs_dim)
        if obs_dim_changed:
            adapted_actor, actor_adapt_info = adapt_actor_state_for_obs_dim(learner.actor, saved_actor_state)
            learner.actor.load_state_dict(adapted_actor, strict=True)
            print(
                f"Adapted actor checkpoint for obs_dim {saved_actor_obs_dim} -> {new_actor_obs_dim}; "
                f"adapted={actor_adapt_info.get('adapted')} skipped={actor_adapt_info.get('skipped')[:8]}",
                flush=True,
            )
        else:
            learner.actor.load_state_dict(saved_actor_state)
        if bool(cfg.get("model", {}).get("physics_blend", {}).get("force_config_after_resume", True)):
            if hasattr(learner.actor, "reset_physics_modes_from_config"):
                learner.actor.reset_physics_modes_from_config(cfg.get("model", {}).get("physics_blend", None))
                print("Applied current config physics_blend/mode_scales after checkpoint load.", flush=True)

        def _load_critic_compat(module, state, label: str):
            if obs_dim_changed:
                adapted, info = adapt_critic_state_for_obs_dim(
                    module, state, old_obs_dim=saved_actor_obs_dim, new_obs_dim=new_actor_obs_dim,
                    priv_dim=priv_dim, action_dim=action_dim,
                )
                module.load_state_dict(adapted, strict=True)
                print(
                    f"Adapted {label} checkpoint for obs_dim {saved_actor_obs_dim} -> {new_actor_obs_dim}; "
                    f"adapted={info.get('adapted')} skipped={info.get('skipped')[:8]}",
                    flush=True,
                )
            else:
                module.load_state_dict(state)

        _load_critic_compat(learner.q1, payload["q1"], "q1")
        _load_critic_compat(learner.q2, payload["q2"], "q2")
        _load_critic_compat(learner.tq1, payload.get("tq1", payload["q1"]), "tq1")
        _load_critic_compat(learner.tq2, payload.get("tq2", payload["q2"]), "tq2")
        # B99 checkpoint resume: cost critics and dual variables exist only in
        # B99+ checkpoints.  B99.6 adds explicit resume controls because it
        # intentionally changes cost definitions while resuming B99.5 iter25.
        resume_cfg = cfg.get("resume", {}) if isinstance(cfg.get("resume", {}), dict) else {}
        load_cost_critics = bool(resume_cfg.get("load_cost_critics", True))
        if load_cost_critics:
            for key, modules in [("cost_q1", learner.cost_q1), ("cost_q2", learner.cost_q2), ("tcost_q1", learner.tcost_q1), ("tcost_q2", learner.tcost_q2)]:
                if isinstance(payload.get(key), dict):
                    for cname, state in payload[key].items():
                        if cname in modules:
                            modules[cname].load_state_dict(state)
        else:
            print("Resume: cost critics are kept at current-config initialization (load_cost_critics=false).", flush=True)

        dual_mode = str(resume_cfg.get("dual_load_mode", "full")).lower()
        if "duals" in payload and dual_mode not in {"none", "ignore", "fresh"}:
            saved_duals = payload.get("duals")
            if dual_mode in {"values_only_current_config", "value_only_current_config", "values_only"} and isinstance(saved_duals, dict):
                current_duals = learner.duals.state_dict()
                for dname, saved in saved_duals.items():
                    if dname in current_duals and isinstance(saved, dict) and "value" in saved:
                        current_duals[dname]["value"] = float(saved["value"])
                learner.duals.load_state_dict(current_duals)
                print("Resume: loaded dual lambda values only; current config target/lr/min/max reapplied.", flush=True)
            else:
                learner.duals.load_state_dict(saved_duals)
        elif dual_mode in {"none", "ignore", "fresh"}:
            print("Resume: dual variables are kept at current-config initialization.", flush=True)

        restore_optim = bool(resume_cfg.get("restore_optimizer_state", True))
        if "actor_opt" in payload and not obs_dim_changed and restore_optim:
            try:
                learner.actor_opt.load_state_dict(payload["actor_opt"])
                learner.critic_opt.load_state_dict(payload["critic_opt"])
                learner.eta_opt.load_state_dict(payload["eta_opt"])
            except Exception as exc:
                print(f"Warning: optimizer state not restored cleanly: {exc}")
        elif obs_dim_changed:
            print("Optimizer states are intentionally not restored because observation inputs changed.", flush=True)
        else:
            print("Resume: optimizer states are reset from current config (restore_optimizer_state=false).", flush=True)
        if "log_eta" in payload:
            with torch.no_grad():
                learner.log_eta.copy_(payload["log_eta"].to(device))
        if bool(resume_cfg.get("reset_update_count", False)):
            learner.update_count = 0
            print("Resume: update_count reset to 0 for the current actor_update_every schedule.", flush=True)
        else:
            learner.update_count = int(payload.get("update_count", 0))
        stats = payload.get("stats", {}) if isinstance(payload.get("stats", {}), dict) else {}
        resume_env_steps = int(stats.get("env_steps", payload.get("env_steps", 0)) or 0)
        resume_iteration = int(stats.get("training_iteration", 0) or 0)
        learner.set_env_steps(resume_env_steps)
        print(f"Resumed MPO checkpoint: {args.resume} env_steps={resume_env_steps} iteration={resume_iteration}", flush=True)

    replay_cfg = cfg.get("replay", {})
    replay = SequenceReplayBuffer(capacity_fragments=int(replay_cfg.get("capacity_fragments", 100000)), seed=int(cfg.get("seed", 42)))
    num_workers = int(par.get("num_tsc_workers", 192))
    fragment_steps = int(par.get("fragment_steps", 32))
    rollout_deterministic = bool(par.get("rollout_deterministic", False))
    print(f"[train_mpo] creating {num_workers} rollout workers", flush=True)
    workers = [MpoRolloutWorker.options(num_cpus=float(par.get("num_cpus_per_tsc_worker", 1))).remote(i, cfg, learner.actor_state_cpu()) for i in range(num_workers)]
    current_reward_params = reward_params_for_global_steps(cfg["train_config_resolved"], resume_env_steps)
    current_target_randomization_params = target_randomization_params_for_global_steps(cfg["train_config_resolved"], resume_env_steps)
    print("[train_mpo] synchronizing initial action_scale/alpha/reward/target-randomization params to workers", flush=True)
    print(f"[train_mpo] target_randomization_stage={current_target_randomization_params.get('stage_name', 'off')} enabled={current_target_randomization_params.get('enabled', False)}", flush=True)
    ray.get([
        w.set_action_scale.remote(
            float(learner.action_scale), float(learner.physics_blend_alpha),
            current_reward_params, current_target_randomization_params,
        )
        for w in workers
    ])
    print("[train_mpo] workers ready; entering rollout loop", flush=True)

    stop_env_steps = int(cfg.get("stop_env_steps", 5_000_000))
    if args.resume and stop_env_steps <= resume_env_steps:
        raise ValueError(
            f"stop_env_steps={stop_env_steps} must be larger than resumed env_steps={resume_env_steps}. "
            "Use a resume config/override with a larger stop_env_steps."
        )
    if args.resume:
        print(f"Resume target: continue from env_steps={resume_env_steps} to stop_env_steps={stop_env_steps} "
              f"(~{stop_env_steps - resume_env_steps} additional env steps).", flush=True)
    warmup_steps = int(cfg.get("mpo", {}).get("warmup_steps", 100_000))
    batch_size = int(cfg.get("mpo", {}).get("batch_size", 256))
    seq_len = int(cfg.get("mpo", {}).get("sequence_len", 32))
    updates_per_iter = int(cfg.get("mpo", {}).get("updates_per_iter", 64))
    checkpoint_every_iters = int(cfg.get("checkpoint_every_iters", 25))
    probe_cfg = cfg.get("deterministic_probe", {})
    probe_enabled = bool(probe_cfg.get("enabled", False))
    probe_every_iters = int(probe_cfg.get("every_iters", checkpoint_every_iters if checkpoint_every_iters > 0 else 25))
    probe_stage = str(probe_cfg.get("eval_stage", "final"))
    probe_seed = int(probe_cfg.get("seed", 12345))
    stoch_probe_cfg = cfg.get("stochastic_probe", {})
    stoch_probe_enabled = bool(stoch_probe_cfg.get("enabled", False))
    stoch_probe_every_iters = int(stoch_probe_cfg.get("every_iters", probe_every_iters))
    stoch_probe_stage = str(stoch_probe_cfg.get("eval_stage", probe_stage))
    stoch_probe_seed = int(stoch_probe_cfg.get("seed", probe_seed + 1000))
    grid_probe_cfg = cfg.get("local_target_grid_probe", {}) or {}
    grid_probe_enabled = bool(grid_probe_cfg.get("enabled", False))
    grid_probe_every_iters = int(grid_probe_cfg.get("every_iters", probe_every_iters))
    grid_probe_stage = str(grid_probe_cfg.get("eval_stage", probe_stage))
    grid_probe_seed = int(grid_probe_cfg.get("seed", probe_seed + 2000))
    sync_every_iters = int(cfg.get("parallel", {}).get("actor_sync_interval_iters", 1))
    results_path = run_dir / "train_results.jsonl"
    csv_path = run_dir / "train_results.csv"
    csv_fields: list[str] = []
    csv_rows: list[dict[str, Any]] = []
    total_steps = int(resume_env_steps)
    iteration = int(resume_iteration)
    start_time = time.time()
    print("[train_mpo] submitting first rollout batch", flush=True)
    pending = {w.rollout.remote(fragment_steps, rollout_deterministic): w for w in workers}
    last_actor_state = learner.actor_state_cpu()
    bad_probe_count = 0
    best_cfg = cfg.get("best_checkpoint", {}) if isinstance(cfg.get("best_checkpoint", {}), dict) else {}
    best_error_score = float("inf")
    best_return = -float("inf")

    try:
        while total_steps < stop_env_steps:
            iteration += 1
            iter_t0 = time.time()
            # Collect one fragment from every worker per iteration.
            collect_t0 = time.time()
            ray_wait_s = 0.0
            ray_get_s = 0.0
            resubmit_s = 0.0
            episodes: list[dict[str, Any]] = []
            frag_rewards = []
            frag_actions = []
            frag_wall_s = []
            frag_env_step_mean_s = []
            frag_env_step_max_s = []
            frag_info_means: dict[str, list[float]] = {}
            frag_info_maxs: dict[str, list[float]] = {}
            for _ in range(num_workers):
                wait_t0 = time.time()
                ready, _ = ray.wait(list(pending.keys()), num_returns=1, timeout=float(par.get("sample_timeout_s", 3600.0)))
                ray_wait_s += time.time() - wait_t0
                if not ready:
                    raise TimeoutError("Timed out waiting for rollout fragment")
                ref = ready[0]
                w = pending.pop(ref)
                get_t0 = time.time()
                data = ray.get(ref)
                ray_get_s += time.time() - get_t0
                replay.add_from_dict(data)
                total_steps += int(data.get("env_steps", 0))
                frag_rewards.append(float(data.get("fragment_mean_reward", 0.0)))
                frag_actions.append(float(data.get("fragment_mean_abs_action", 0.0)))
                frag_wall_s.append(float(data.get("fragment_wall_s", 0.0)))
                frag_env_step_mean_s.append(float(data.get("env_step_wall_s_mean", 0.0)))
                frag_env_step_max_s.append(float(data.get("env_step_wall_s_max", 0.0)))
                for mk, mv in dict(data.get("fragment_info_means", {}) or {}).items():
                    if isinstance(mv, (int, float)) and np.isfinite(float(mv)):
                        frag_info_means.setdefault(str(mk), []).append(float(mv))
                for mk, mv in dict(data.get("fragment_info_maxs", {}) or {}).items():
                    if isinstance(mv, (int, float)) and np.isfinite(float(mv)):
                        frag_info_maxs.setdefault(str(mk), []).append(float(mv))
                episodes.extend(list(data.get("episodes", [])))
                submit_t0 = time.time()
                pending[w.rollout.remote(fragment_steps, rollout_deterministic)] = w
                resubmit_s += time.time() - submit_t0
            collect_s = time.time() - collect_t0

            losses = []
            learner_t0 = time.time()
            learner_train_s = 0.0
            learner_sample_batch_s = 0.0
            learner_update_call_s = 0.0
            worker_param_rpc_s = 0.0
            pipeline_wait_s = 0.0
            learner.set_env_steps(total_steps)
            current_reward_params = reward_params_for_global_steps(cfg["train_config_resolved"], total_steps)
            current_target_randomization_params = target_randomization_params_for_global_steps(cfg["train_config_resolved"], total_steps)
            if total_steps >= warmup_steps and replay.can_sample(batch_size, seq_len):
                train_t0 = time.time()
                for _ in range(updates_per_iter):
                    sample_t0 = time.time()
                    batch = replay.sample(batch_size=batch_size, seq_len=seq_len)
                    learner_sample_batch_s += time.time() - sample_t0
                    upd_t0 = time.time()
                    losses.append(learner.update(batch))
                    learner_update_call_s += time.time() - upd_t0
                learner_train_s = time.time() - train_t0
                if iteration % sync_every_iters == 0:
                    last_actor_state = learner.actor_state_cpu()
                    sync_t0 = time.time()
                    ray.get([
                        w.set_actor_weights.remote(
                            last_actor_state, float(learner.action_scale), float(learner.physics_blend_alpha),
                            current_reward_params, current_target_randomization_params,
                        )
                        for w in workers
                    ])
                    worker_param_rpc_s += time.time() - sync_t0
            elif iteration % sync_every_iters == 0:
                # During warmup the actor weights and scale normally do not change.
                # Skipping this RPC avoids a misleading pipeline-wait timing block.
                # If future schedules change action_scale during warmup, force sync by
                # setting parallel.force_warmup_param_sync=true.
                if bool(cfg.get("parallel", {}).get("force_warmup_param_sync", False)):
                    sync_t0 = time.time()
                    ray.get([
                        w.set_action_scale.remote(
                            float(learner.action_scale), float(learner.physics_blend_alpha),
                            current_reward_params, current_target_randomization_params,
                        )
                        for w in workers
                    ])
                    worker_param_rpc_s += time.time() - sync_t0
            learner_total_s = time.time() - learner_t0
            pipeline_wait_s = max(0.0, worker_param_rpc_s - 0.0)  # RPC may include Ray actor queue wait behind rollout.
            # Backward-compatible names for older CSV readers; prefer the B99.3 names below.
            actor_sync_s = worker_param_rpc_s
            learner_update_s = learner_total_s

            loss_mean = {}
            if losses:
                for k in losses[0].keys():
                    loss_mean[k] = float(np.mean([x[k] for x in losses if k in x]))

            ep_summary = summarize_episodes(episodes)
            elapsed = time.time() - start_time
            result = {
                "training_iteration": iteration,
                "env_steps": int(total_steps),
                "time_total_s": float(elapsed),
                "time_this_iter_s": float(time.time() - iter_t0),
                "env_steps_per_s_total": float(total_steps / max(elapsed, 1.0e-9)),
                "timing/rollout_collect_s": float(collect_s),
                "timing/ray_wait_s": float(ray_wait_s),
                "timing/ray_get_s": float(ray_get_s),
                "timing/resubmit_s": float(resubmit_s),
                "timing/learner_update_s": float(learner_update_s),
                "timing/actor_sync_s": float(actor_sync_s),
                "timing/learner_total_s": float(learner_total_s),
                "timing/learner_train_s": float(learner_train_s),
                "timing/learner_sample_batch_s": float(learner_sample_batch_s),
                "timing/learner_update_call_s": float(learner_update_call_s),
                "timing/worker_param_rpc_s": float(worker_param_rpc_s),
                "timing/pipeline_wait_s": float(pipeline_wait_s),
                "worker/fragment_wall_s_mean": float(np.mean(frag_wall_s)) if frag_wall_s else 0.0,
                "worker/fragment_wall_s_max": float(np.max(frag_wall_s)) if frag_wall_s else 0.0,
                "worker/env_step_wall_s_mean": float(np.mean(frag_env_step_mean_s)) if frag_env_step_mean_s else 0.0,
                "worker/env_step_wall_s_max": float(np.max(frag_env_step_max_s)) if frag_env_step_max_s else 0.0,
                **{f"worker/{k}_mean": float(np.mean(vs)) for k, vs in frag_info_means.items() if vs},
                **{f"worker/{k}_max": float(np.max(vs)) for k, vs in frag_info_maxs.items() if vs},
                "fragment_mean_reward": float(np.mean(frag_rewards)) if frag_rewards else 0.0,
                "fragment_mean_abs_action": float(np.mean(frag_actions)) if frag_actions else 0.0,
                "updates_this_iter": int(len(losses)),
                "actor_action_scale": float(learner.action_scale),
                "actor_physics_blend_alpha": float(learner.physics_blend_alpha),
                "target_randomization_stage": str(target_randomization_params_for_global_steps(cfg["train_config_resolved"], total_steps).get("stage_name", "off")),
                "target_randomization_enabled": bool(target_randomization_params_for_global_steps(cfg["train_config_resolved"], total_steps).get("enabled", False)),
                "target_fixed_probability": float(target_randomization_params_for_global_steps(cfg["train_config_resolved"], total_steps).get("fixed_probability", 0.0)),
                **{f"learner/{k}": v for k, v in loss_mean.items()},
                **{f"replay/{k}": v for k, v in replay.stats().items()},
                **ep_summary,
            }
            stop_now = False
            probe_for_early_stop = None
            eval_t0 = time.time()
            if probe_enabled and probe_every_iters > 0 and iteration % probe_every_iters == 0:
                try:
                    probe = run_online_deterministic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=probe_seed, stage=probe_stage
                    )
                    probe_for_early_stop = probe
                    result.update(probe)
                except Exception as exc:
                    result["eval_final_det_error"] = repr(exc)
            if stoch_probe_enabled and stoch_probe_every_iters > 0 and iteration % stoch_probe_every_iters == 0:
                try:
                    stoch_probe = run_online_stochastic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=stoch_probe_seed + iteration, stage=stoch_probe_stage
                    )
                    result.update(stoch_probe)
                except Exception as exc:
                    result["eval_final_stoch_error"] = repr(exc)
            if grid_probe_enabled and grid_probe_every_iters > 0 and iteration % grid_probe_every_iters == 0:
                try:
                    grid_probe = run_online_local_target_grid_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=grid_probe_seed + iteration, stage=grid_probe_stage
                    )
                    result.update(grid_probe)
                except Exception as exc:
                    result["eval_grid_error"] = repr(exc)
            result["timing/eval_probe_s"] = float(time.time() - eval_t0)
            if probe_for_early_stop is not None:
                stop_now, bad_probe_count, reason = should_early_stop_from_probe(cfg, iteration, probe_for_early_stop, bad_probe_count)
                result["early_stop_bad_probe_count"] = int(bad_probe_count)
                result["early_stop_reason"] = str(reason)
                result["early_stop_triggered"] = bool(stop_now)
            best_t0 = time.time()
            result["best/error_score"] = compute_checkpoint_error_score(result, best_cfg)
            min_eps_best = int(best_cfg.get("min_episodes_completed", 1) or 1)
            has_eps_best = int(result.get("episodes_completed", 0) or 0) >= min_eps_best
            if bool(best_cfg.get("enabled", False)) and has_eps_best:
                if bool(best_cfg.get("save_best_by_error_score", True)) and result["best/error_score"] < best_error_score:
                    best_error_score = float(result["best/error_score"])
                    result["best/error_score_improved"] = True
                    result["best/error_score_best_so_far"] = float(best_error_score)
                    learner.save_checkpoint(ckpt_dir / str(best_cfg.get("directory_error_score", "best_error_score")), result)
                else:
                    result["best/error_score_improved"] = False
                    result["best/error_score_best_so_far"] = float(best_error_score)
                ep_ret = float(result.get("episode_episode_return_mean", -float("inf")) or -float("inf"))
                if bool(best_cfg.get("save_best_by_return", False)) and np.isfinite(ep_ret) and ep_ret > best_return:
                    best_return = float(ep_ret)
                    result["best/return_improved"] = True
                    result["best/return_best_so_far"] = float(best_return)
                    learner.save_checkpoint(ckpt_dir / str(best_cfg.get("directory_return", "best_return")), result)
                else:
                    result["best/return_improved"] = False
                    result["best/return_best_so_far"] = float(best_return)
            result["timing/best_checkpoint_s"] = float(time.time() - best_t0)
            io_t0 = time.time()
            safe_result = json_safe(result)
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(safe_result, ensure_ascii=False) + "\n")
            csv_rows.append(safe_result)
            added_fields = False
            for key in safe_result.keys():
                if key not in csv_fields:
                    csv_fields.append(str(key))
                    added_fields = True
            if added_fields or not csv_path.exists():
                write_dynamic_csv(csv_path, csv_rows, csv_fields)
            else:
                with open(csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
                    writer.writerow(safe_result)

            result["timing/log_write_s"] = float(time.time() - io_t0)
            print(json.dumps(json_safe(result), ensure_ascii=False), flush=True)
            if checkpoint_every_iters > 0 and iteration % checkpoint_every_iters == 0:
                ckpt_t0 = time.time()
                learner.save_checkpoint(ckpt_dir / f"iter_{iteration:06d}", result)
                result["timing/checkpoint_s"] = float(time.time() - ckpt_t0)
            if bool(result.get("early_stop_triggered", False)):
                print(f"MPO early stop triggered at iter={iteration}: {result.get('early_stop_reason')}", flush=True)
                break
            if total_steps >= stop_env_steps:
                break
    finally:
        final_eval_cfg = cfg.get("final_evaluation", {}) or {}
        if bool(final_eval_cfg.get("enabled", False)):
            final_summary: dict[str, Any] = {
                "training_iteration": int(iteration),
                "env_steps": int(total_steps),
                "final_evaluation": True,
            }
            final_t0 = time.time()
            try:
                if bool(final_eval_cfg.get("deterministic_fixed", True)):
                    final_summary.update(run_online_deterministic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=int(final_eval_cfg.get("seed", 92345)),
                        stage=str(final_eval_cfg.get("eval_stage", "final")),
                    ))
                if bool(final_eval_cfg.get("stochastic_fixed", False)):
                    final_summary.update(run_online_stochastic_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=int(final_eval_cfg.get("seed", 92345)) + 1000,
                        stage=str(final_eval_cfg.get("eval_stage", "final")),
                    ))
                if bool(final_eval_cfg.get("grid", True)):
                    final_summary.update(run_online_local_target_grid_probe(
                        cfg, learner, iteration=iteration, env_steps=total_steps,
                        seed=int(final_eval_cfg.get("seed", 92345)) + 2000,
                        stage=str(final_eval_cfg.get("eval_stage", "final")),
                    ))
            except Exception as exc:
                final_summary["final_eval_error"] = repr(exc)
            final_summary["timing/final_eval_s"] = float(time.time() - final_t0)
            with open(run_dir / "final_eval_summary.json", "w", encoding="utf-8") as f:
                json.dump(json_safe(final_summary), f, indent=2, ensure_ascii=False)
            try:
                with open(results_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(json_safe(final_summary), ensure_ascii=False) + "\n")
            except Exception:
                pass
            print(json.dumps(json_safe(final_summary), ensure_ascii=False), flush=True)
        try:
            ray.get([w.close.remote() for w in workers], timeout=60)
        except Exception:
            pass
        learner.save_checkpoint(ckpt_dir / "final", {"training_iteration": iteration, "env_steps": total_steps, "time_total_s": time.time() - start_time})
        with open(run_dir / "disk_health_latest.json", "w", encoding="utf-8") as f:
            json.dump(disk_health_report([run_dir, ckpt_dir, Path(os.environ["RAY_TMPDIR"])]), f, indent=2)
        ray.shutdown()

    print(f"MPO training finished. run_dir={run_dir} checkpoint_dir={ckpt_dir}")


if __name__ == "__main__":
    main()
