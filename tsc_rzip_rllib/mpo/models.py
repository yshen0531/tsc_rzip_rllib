from __future__ import annotations

import math
from typing import Iterable, Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal

LOG_STD_MIN = -5.0
LOG_STD_MAX = 2.0
EPS = 1.0e-6


def mlp(sizes: Iterable[int], activation: str = "silu", *, last_activation: bool = False) -> nn.Sequential:
    sizes = list(map(int, sizes))
    acts = {
        "relu": nn.ReLU,
        "tanh": nn.Tanh,
        "silu": nn.SiLU,
        "swish": nn.SiLU,
        "elu": nn.ELU,
    }
    act_cls = acts.get(str(activation).lower(), nn.SiLU)
    layers: list[nn.Module] = []
    for i in range(len(sizes) - 1):
        layers.append(nn.Linear(sizes[i], sizes[i + 1]))
        if i < len(sizes) - 2 or last_activation:
            layers.append(act_cls())
    return nn.Sequential(*layers)


def default_physics_mode_matrix(action_dim: int) -> tuple[list[str], torch.Tensor]:
    """Default B90 split physics-informed action modes for the 14D CSPF action order.

    Action order assumed by the current TSC-RZIP setup:
      CS1U, CS1L, CS2U, CS2L, CS3U, CS3L, CS4U, CS4L,
      PF2U, PF2L, PF3U, PF3L, PF4U, PF4L

    The signs of the mode coefficients are learned by the actor.  These rows only
    encode weak structural priors: U/L differential channels for vertical/shape
    asymmetry and U/L common channels for flux/radial/Ip-like corrections.
    """
    if int(action_dim) != 14:
        return [], torch.zeros(0, int(action_dim), dtype=torch.float32)

    rows: list[list[float]] = []
    names: list[str] = []

    def add(name: str, vals: dict[int, float]):
        row = [0.0] * 14
        for k, v in vals.items():
            row[int(k)] = float(v)
        rows.append(row)
        names.append(name)

    # B90 default: split high-Z PF U/L differential channels so the learner can
    # discover which PF pair actually moves Z in the useful direction.
    add("pf2_vertical_diff", {8: 1.0, 9: -1.0})
    add("pf3_vertical_diff", {10: 1.0, 11: -1.0})
    add("pf4_vertical_diff", {12: 1.0, 13: -1.0})
    add("pf23_vertical_diff", {8: 0.8, 9: -0.8, 10: 1.0, 11: -1.0})
    add("pf34_vertical_diff", {10: 1.0, 11: -1.0, 12: 0.6, 13: -0.6})
    # Weaker CS differential vertical auxiliary prior.
    add("cs_aux_vertical_diff", {0: 0.20, 1: -0.20, 2: 0.50, 3: -0.50, 4: 0.80, 5: -0.80, 6: 1.0, 7: -1.0})
    # Outer common PF channel for radial/shape/flux trim.
    add("outer_pf_common_shape", {8: 0.33, 9: 0.33, 10: 0.78, 11: 0.78, 12: 1.0, 13: 1.0})
    # CS common flux/Ip-like weak guard channel.
    add("cs_common_flux", {0: 0.70, 1: 0.70, 2: 0.85, 3: 0.85, 4: 1.0, 5: 1.0, 6: 0.85, 7: 0.85})
    # Mixed Z-shape mode: high-Z PF differential plus a small outer common counter-term.
    add("mixed_pf_z_shape", {8: 0.60, 9: -0.60, 10: 0.80, 11: -0.80, 12: -0.25, 13: -0.25})

    return names, torch.tensor(rows, dtype=torch.float32)


def build_mode_matrix(action_dim: int, physics_blend: dict[str, Any] | None) -> tuple[list[str], torch.Tensor]:
    cfg = physics_blend or {}
    if not bool(cfg.get("enabled", False)):
        return [], torch.zeros(0, int(action_dim), dtype=torch.float32)
    if "mode_matrix" in cfg and cfg["mode_matrix"]:
        mat = torch.tensor(cfg["mode_matrix"], dtype=torch.float32)
        names = [str(x) for x in cfg.get("mode_names", [f"mode_{i}" for i in range(mat.shape[0])])]
    else:
        names, mat = default_physics_mode_matrix(int(action_dim))
    if mat.ndim != 2 or mat.shape[1] != int(action_dim):
        raise ValueError(f"physics_blend.mode_matrix must have shape [mode_dim,{action_dim}], got {tuple(mat.shape)}")
    if len(names) != int(mat.shape[0]):
        names = [f"mode_{i}" for i in range(int(mat.shape[0]))]

    # Optional per-mode gain.  This is deliberately implemented as a matrix-row
    # scale rather than a new learnable parameter, so B91 remains checkpoint-
    # compatible with B90 as long as the number of modes is unchanged.
    mode_scales = cfg.get("mode_scales", None)
    if isinstance(mode_scales, dict) and mat.numel() > 0:
        scale_vec = torch.ones(int(mat.shape[0]), dtype=torch.float32)
        for i, name in enumerate(names):
            if name in mode_scales:
                scale_vec[i] = float(mode_scales[name])
        mat = mat * scale_vec.view(-1, 1)
    elif isinstance(mode_scales, (list, tuple)) and mat.numel() > 0:
        if len(mode_scales) != int(mat.shape[0]):
            raise ValueError(
                f"physics_blend.mode_scales list must have length {int(mat.shape[0])}, got {len(mode_scales)}"
            )
        mat = mat * torch.tensor(mode_scales, dtype=torch.float32).view(-1, 1)

    if bool(cfg.get("normalize_modes", False)) and mat.numel() > 0:
        denom = torch.clamp(mat.abs().amax(dim=1, keepdim=True), min=1.0e-12)
        mat = mat / denom
    return names, mat


class RecurrentGaussianActor(nn.Module):
    """Deployable recurrent actor.

    Optionally augment the raw 14D action head with a weak physics-informed
    mode head.  The actor still learns all mode coefficients and all raw residuals;
    physics only defines a fixed action subspace prior.
    """

    def __init__(
        self,
        obs_dim: int,
        action_dim: int,
        hidden_size: int = 128,
        mlp_hiddens: list[int] | tuple[int, ...] = (256, 256),
        activation: str = "silu",
        log_std_min: float = LOG_STD_MIN,
        log_std_max: float = LOG_STD_MAX,
        physics_blend: dict[str, Any] | None = None,
    ):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.hidden_size = int(hidden_size)
        self.log_std_min = float(log_std_min)
        self.log_std_max = float(log_std_max)

        pcfg = physics_blend or {}
        mode_names, mode_matrix = build_mode_matrix(self.action_dim, pcfg)
        self.physics_blend_enabled = bool(pcfg.get("enabled", False)) and mode_matrix.numel() > 0
        self.physics_mode_names = mode_names
        self.physics_mode_dim = int(mode_matrix.shape[0]) if self.physics_blend_enabled else 0
        self.latent_dim = self.action_dim + self.physics_mode_dim
        self.physics_mode_scale = float(pcfg.get("mode_scale", 1.0))
        self.physics_action_clip = float(pcfg.get("physics_action_clip", 1.0))
        self.raw_action_scale = float(pcfg.get("raw_action_scale", 1.0))
        self.register_buffer("physics_mode_matrix", mode_matrix if self.physics_blend_enabled else torch.zeros(0, self.action_dim))
        self.register_buffer("physics_blend_alpha", torch.tensor(float(pcfg.get("alpha_init", pcfg.get("alpha", 0.0))), dtype=torch.float32))

        self.gru = nn.GRU(input_size=self.obs_dim, hidden_size=self.hidden_size, batch_first=True)
        self.trunk = mlp([self.hidden_size, *map(int, mlp_hiddens)], activation=activation, last_activation=True)
        last = int(mlp_hiddens[-1]) if mlp_hiddens else self.hidden_size
        self.mean = nn.Linear(last, self.latent_dim)
        self.log_std = nn.Linear(last, self.latent_dim)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
        nn.init.uniform_(self.mean.weight, -1.0e-3, 1.0e-3)
        nn.init.uniform_(self.mean.bias, -1.0e-3, 1.0e-3)

    def init_hidden(self, batch_size: int, device: torch.device | str | None = None) -> torch.Tensor:
        return torch.zeros(1, int(batch_size), self.hidden_size, device=device)

    def set_physics_blend_alpha(self, alpha: float) -> None:
        with torch.no_grad():
            self.physics_blend_alpha.fill_(float(alpha))

    def reset_physics_modes_from_config(self, physics_blend: dict[str, Any] | None) -> None:
        """Refresh fixed physics-mode buffers from the currently requested config.

        This is useful when B91 resumes from a B90 checkpoint: the trainable actor
        parameters are compatible, but state_dict loading also restores the old
        physics_mode_matrix buffer.  Re-applying the config after load ensures
        mode_scales/matrix edits actually take effect.
        """
        pcfg = physics_blend or {}
        mode_names, mode_matrix = build_mode_matrix(self.action_dim, pcfg)
        enabled = bool(pcfg.get("enabled", False)) and mode_matrix.numel() > 0
        expected_dim = self.physics_mode_dim
        new_dim = int(mode_matrix.shape[0]) if enabled else 0
        if new_dim != expected_dim:
            raise ValueError(
                f"Cannot reset physics modes with different mode_dim: checkpoint actor has {expected_dim}, "
                f"config requests {new_dim}. Start from scratch or keep mode count unchanged."
            )
        self.physics_blend_enabled = bool(enabled)
        self.physics_mode_names = mode_names
        self.physics_mode_scale = float(pcfg.get("mode_scale", 1.0))
        self.physics_action_clip = float(pcfg.get("physics_action_clip", 1.0))
        self.raw_action_scale = float(pcfg.get("raw_action_scale", 1.0))
        with torch.no_grad():
            if enabled:
                self.physics_mode_matrix.copy_(mode_matrix.to(
                    dtype=self.physics_mode_matrix.dtype, device=self.physics_mode_matrix.device
                ))

    def forward(
        self,
        obs_seq: torch.Tensor,
        hidden: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if obs_seq.ndim == 2:
            obs_seq = obs_seq.unsqueeze(1)
        out, h = self.gru(obs_seq, hidden)
        z = self.trunk(out)
        mean = self.mean(z)
        log_std = torch.clamp(self.log_std(z), self.log_std_min, self.log_std_max)
        return mean, log_std, h

    def distribution(self, obs_seq: torch.Tensor, hidden: torch.Tensor | None = None):
        mean, log_std, h = self.forward(obs_seq, hidden)
        return Normal(mean, log_std.exp()), mean, log_std, h

    def action_components_from_pre_tanh(self, pre_tanh: torch.Tensor) -> dict[str, torch.Tensor]:
        raw_pre = pre_tanh[..., : self.action_dim]
        raw_action = torch.tanh(raw_pre) * self.raw_action_scale
        if self.physics_blend_enabled and self.physics_mode_dim > 0:
            mode_pre = pre_tanh[..., self.action_dim : self.action_dim + self.physics_mode_dim]
            mode_coeff = torch.tanh(mode_pre) * self.physics_mode_scale
            physics_action = torch.matmul(mode_coeff, self.physics_mode_matrix.to(dtype=pre_tanh.dtype, device=pre_tanh.device))
            if self.physics_action_clip > 0:
                physics_action = torch.clamp(physics_action, -self.physics_action_clip, self.physics_action_clip)
            alpha = torch.clamp(self.physics_blend_alpha.to(dtype=pre_tanh.dtype, device=pre_tanh.device), 0.0, 1.0)
            blended = (1.0 - alpha) * raw_action + alpha * physics_action
        else:
            mode_coeff = pre_tanh.new_zeros(*pre_tanh.shape[:-1], 0)
            physics_action = pre_tanh.new_zeros(*pre_tanh.shape[:-1], self.action_dim)
            blended = raw_action
        blended = torch.clamp(blended, -1.0, 1.0)
        return {
            "raw_action": raw_action,
            "physics_action": physics_action,
            "mode_coeff": mode_coeff,
            "blended_action": blended,
        }

    def action_from_pre_tanh(self, pre_tanh: torch.Tensor, action_scale: float | torch.Tensor = 1.0) -> torch.Tensor:
        return self.action_components_from_pre_tanh(pre_tanh)["blended_action"] * action_scale

    def sample(
        self,
        obs_seq: torch.Tensor,
        hidden: torch.Tensor | None = None,
        deterministic: bool = False,
        action_scale: float | torch.Tensor = 1.0,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        dist, mean, log_std, h = self.distribution(obs_seq, hidden)
        if deterministic:
            pre_tanh = mean
        else:
            pre_tanh = dist.rsample()
        action = self.action_from_pre_tanh(pre_tanh, action_scale=action_scale)
        # The constant log(action_scale) term is omitted because action_scale is
        # externally scheduled and independent of policy parameters.
        logp = tanh_gaussian_log_prob(pre_tanh, mean, log_std)
        return action, logp, h, mean, log_std

    @torch.no_grad()
    def act_step(
        self,
        obs: torch.Tensor,
        hidden: torch.Tensor | None,
        deterministic: bool = False,
        action_scale: float | torch.Tensor = 1.0,
    ):
        if obs.ndim == 1:
            obs = obs.view(1, 1, -1)
        elif obs.ndim == 2:
            obs = obs.unsqueeze(1)
        action, _, h, _, _ = self.sample(obs, hidden, deterministic=deterministic, action_scale=action_scale)
        return action[:, -1, :], h


class RecurrentQCritic(nn.Module):
    """Asymmetric recurrent critic.

    Critic sees deployable obs + critic-only privileged features + final action.
    """

    def __init__(
        self,
        obs_dim: int,
        priv_dim: int,
        action_dim: int,
        hidden_size: int = 256,
        mlp_hiddens: list[int] | tuple[int, ...] = (512, 512),
        activation: str = "silu",
    ):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.priv_dim = int(priv_dim)
        self.action_dim = int(action_dim)
        self.hidden_size = int(hidden_size)
        in_dim = self.obs_dim + self.priv_dim + self.action_dim
        self.gru = nn.GRU(input_size=in_dim, hidden_size=self.hidden_size, batch_first=True)
        self.head = mlp([self.hidden_size, *map(int, mlp_hiddens), 1], activation=activation)
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(
        self,
        obs_seq: torch.Tensor,
        priv_seq: torch.Tensor,
        action_seq: torch.Tensor,
        hidden: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if obs_seq.ndim == 2:
            obs_seq = obs_seq.unsqueeze(1)
        if priv_seq.ndim == 2:
            priv_seq = priv_seq.unsqueeze(1)
        if action_seq.ndim == 2:
            action_seq = action_seq.unsqueeze(1)
        x = torch.cat([obs_seq, priv_seq, action_seq], dim=-1)
        out, _ = self.gru(x, hidden)
        q = self.head(out).squeeze(-1)
        return q


def tanh_gaussian_log_prob(pre_tanh: torch.Tensor, mean: torch.Tensor, log_std: torch.Tensor) -> torch.Tensor:
    std = log_std.exp()
    normal = Normal(mean, std)
    logp = normal.log_prob(pre_tanh).sum(dim=-1)
    # Tanh change-of-variables correction.
    # log(1 - tanh(x)^2) = 2*(log(2) - x - softplus(-2x)) is stable.
    correction = (2.0 * (math.log(2.0) - pre_tanh - F.softplus(-2.0 * pre_tanh))).sum(dim=-1)
    return logp - correction


def tanh_gaussian_log_prob_from_action(action: torch.Tensor, mean: torch.Tensor, log_std: torch.Tensor) -> torch.Tensor:
    action = torch.clamp(action, -1.0 + EPS, 1.0 - EPS)
    pre_tanh = 0.5 * torch.log((1.0 + action) / (1.0 - action))
    return tanh_gaussian_log_prob(pre_tanh, mean, log_std)


def gaussian_kl(old_mean: torch.Tensor, old_log_std: torch.Tensor, new_mean: torch.Tensor, new_log_std: torch.Tensor) -> torch.Tensor:
    """KL(old || new) for diagonal Gaussians, summed over latent dim."""
    old_var = torch.exp(2.0 * old_log_std)
    new_var = torch.exp(2.0 * new_log_std)
    kl = new_log_std - old_log_std + (old_var + (old_mean - new_mean).pow(2)) / (2.0 * new_var + EPS) - 0.5
    return kl.sum(dim=-1)


def soft_update(target: nn.Module, source: nn.Module, tau: float) -> None:
    with torch.no_grad():
        for tp, sp in zip(target.parameters(), source.parameters()):
            tp.data.mul_(1.0 - tau).add_(sp.data, alpha=float(tau))


def hard_update(target: nn.Module, source: nn.Module) -> None:
    target.load_state_dict(source.state_dict())
