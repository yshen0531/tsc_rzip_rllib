from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch


@dataclass
class DualState:
    name: str
    value: float
    target: float
    lr: float
    min_value: float
    max_value: float


class MultiplicativeDuals:
    """Small CPU-side multiplicative dual update helper for constrained RL.

    The user specifies constraint targets (engineering specs) while the effective
    Lagrange multipliers are adapted from observed violations.  This avoids using
    hand-picked scalar reward weights as the main balancing mechanism.
    """

    def __init__(self, cfg: dict[str, Any] | None, names: list[str]):
        raw = cfg or {}
        self.names = list(names)
        default_init = float(raw.get("init", 1.0))
        default_target = float(raw.get("target", 0.0))
        default_lr = float(raw.get("lr", 0.02))
        default_min = float(raw.get("min", 0.0))
        default_max = float(raw.get("max", 100.0))
        per = raw.get("per_cost", {}) if isinstance(raw.get("per_cost", {}), dict) else {}
        self.state: dict[str, DualState] = {}
        for name in self.names:
            pc = per.get(name, {}) if isinstance(per.get(name, {}), dict) else {}
            self.state[name] = DualState(
                name=name,
                value=float(pc.get("init", default_init)),
                target=float(pc.get("target", default_target)),
                lr=float(pc.get("lr", default_lr)),
                min_value=float(pc.get("min", default_min)),
                max_value=float(pc.get("max", default_max)),
            )

    def values_tensor(self, *, device: torch.device | str, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        return torch.tensor([self.state[n].value for n in self.names], dtype=dtype, device=device)

    def targets_tensor(self, *, device: torch.device | str, dtype: torch.dtype = torch.float32) -> torch.Tensor:
        return torch.tensor([self.state[n].target for n in self.names], dtype=dtype, device=device)

    def update(self, observed: np.ndarray | list[float] | torch.Tensor, *, rate_scale: float = 1.0) -> dict[str, float]:
        if isinstance(observed, torch.Tensor):
            arr = observed.detach().cpu().numpy().astype(float).reshape(-1)
        else:
            arr = np.asarray(observed, dtype=float).reshape(-1)
        for i, name in enumerate(self.names):
            if i >= arr.size or not np.isfinite(arr[i]):
                continue
            st = self.state[name]
            # Multiplicative update: lambda *= exp(rate_scale * lr * violation).
            rs = max(0.0, float(rate_scale))
            new_value = st.value * math.exp(rs * st.lr * (float(arr[i]) - st.target))
            st.value = float(min(max(new_value, st.min_value), st.max_value))
        return self.as_metrics(prefix="dual")

    def state_dict(self) -> dict[str, Any]:
        return {name: vars(st).copy() for name, st in self.state.items()}

    def load_state_dict(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        for name, st_data in data.items():
            if name not in self.state or not isinstance(st_data, dict):
                continue
            st = self.state[name]
            for attr in ("value", "target", "lr", "min_value", "max_value"):
                if attr in st_data:
                    setattr(st, attr, float(st_data[attr]))

    def as_metrics(self, prefix: str = "dual") -> dict[str, float]:
        out: dict[str, float] = {}
        for name in self.names:
            st = self.state[name]
            out[f"{prefix}/lambda_{name}"] = float(st.value)
            out[f"{prefix}/target_{name}"] = float(st.target)
            out[f"{prefix}/lr_{name}"] = float(st.lr)
        return out
