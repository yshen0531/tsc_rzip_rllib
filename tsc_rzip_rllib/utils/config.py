from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    return json.loads(path.read_text())


def deep_update(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively update base dict with override dict.

    Rules:
        - dict + dict: recursively merge
        - list/scalar/None: override replaces base value
        - base is not modified in-place
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def load_train_config(
    base_config_path: str | Path,
    debug: bool = False,
    debug_config_path: str | Path | None = None,
) -> dict[str, Any]:
    base_cfg = load_json(base_config_path)

    if not debug:
        return base_cfg

    if debug_config_path is None:
        raise ValueError("debug=True but debug_config_path is None.")

    debug_path = Path(debug_config_path)
    if not debug_path.exists():
        raise FileNotFoundError(f"debug config not found: {debug_path}")

    debug_cfg = load_json(debug_path)
    merged = deep_update(base_cfg, debug_cfg)
    merged["_debug"] = {
        "enabled": True,
        "base_config_path": str(base_config_path),
        "debug_config_path": str(debug_path),
    }
    return merged


def available_cpu_count() -> int:
    """Return CPU count available to this process when possible.

    On Linux clusters, os.sched_getaffinity(0) usually reflects the CPUs
    allowed by cpuset/cgroup/taskset. If unavailable, fall back to os.cpu_count().
    """
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except Exception:
        return max(1, os.cpu_count() or 1)


def _parse_n_envs_spec(spec: Any) -> int | float:
    if spec is None:
        return 0.5

    if isinstance(spec, bool):
        raise ValueError("n_envs must be int or float, not bool.")

    if isinstance(spec, int):
        if spec < 1:
            raise ValueError("integer n_envs must be >= 1.")
        return spec

    if isinstance(spec, float):
        if spec <= 0:
            raise ValueError("float n_envs must be > 0.")
        if spec >= 1 and not spec.is_integer():
            raise ValueError("float n_envs >= 1 must be integer-valued, e.g. 2.0.")
        return spec

    if isinstance(spec, str):
        text = spec.strip().lower()
        if text in {"half", "half_cpu", "auto"}:
            return 0.5

        try:
            if "." in text:
                value = float(text)
                if value <= 0:
                    raise ValueError
                if value >= 1 and not value.is_integer():
                    raise ValueError
                return value
            value = int(text)
            if value < 1:
                raise ValueError
            return value
        except ValueError as exc:
            raise ValueError(
                f"Invalid n_envs spec {spec!r}. Use 0<x<1 as CPU fraction, "
                "or positive integer >=1."
            ) from exc

    raise TypeError(f"Unsupported n_envs spec type: {type(spec).__name__}")


def resolve_n_envs(
    spec: Any,
    *,
    max_fraction: float = 0.5,
) -> tuple[int, dict[str, Any]]:
    """Resolve n_envs from either fraction or integer.

    User rule:
        - if 0 < spec < 1: n_envs = int(spec * available_cpus)
        - if spec >= 1: spec must be integer, n_envs = spec
        - always clamp to [1, int(max_fraction * available_cpus)]
    """
    total_cpus = available_cpu_count()
    max_allowed = max(1, int(total_cpus * max_fraction))

    parsed = _parse_n_envs_spec(spec)

    if isinstance(parsed, float) and parsed < 1:
        requested = int(total_cpus * parsed)
    else:
        requested = int(parsed)

    requested = max(1, requested)
    resolved = min(requested, max_allowed)

    info = {
        "input_spec": spec,
        "parsed_spec": parsed,
        "available_cpus": total_cpus,
        "max_fraction": max_fraction,
        "max_allowed": max_allowed,
        "requested_n_envs": requested,
        "resolved_n_envs": resolved,
        "capped": requested != resolved,
    }

    return resolved, info