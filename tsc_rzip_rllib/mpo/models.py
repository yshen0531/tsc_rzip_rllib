from __future__ import annotations

import math
from typing import Iterable

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


class RecurrentGaussianActor(nn.Module):
    """Deployable recurrent actor.

    Input is deployable observation only.  It outputs a tanh-squashed Gaussian
    action distribution in normalized [-1, 1]^action_dim.
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
    ):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.action_dim = int(action_dim)
        self.hidden_size = int(hidden_size)
        self.log_std_min = float(log_std_min)
        self.log_std_max = float(log_std_max)
        self.gru = nn.GRU(input_size=self.obs_dim, hidden_size=self.hidden_size, batch_first=True)
        self.trunk = mlp([self.hidden_size, *map(int, mlp_hiddens)], activation=activation, last_activation=True)
        last = int(mlp_hiddens[-1]) if mlp_hiddens else self.hidden_size
        self.mean = nn.Linear(last, self.action_dim)
        self.log_std = nn.Linear(last, self.action_dim)
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
        action = torch.tanh(pre_tanh) * action_scale
        # The constant log(action_scale) term is omitted because action_scale is
        # externally scheduled and independent of policy parameters.  Keeping the
        # same tanh-Gaussian likelihood preserves the MPO weighted M-step while
        # hard-limiting the action actually sent to the plant.
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

    Critic sees deployable obs + critic-only privileged features + action.
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
    """KL(old || new) for diagonal Gaussians, summed over action dim."""
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
