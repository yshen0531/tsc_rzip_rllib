from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Fragment:
    obs: np.ndarray
    priv: np.ndarray
    action: np.ndarray
    reward: np.ndarray
    done: np.ndarray
    cost: np.ndarray
    next_obs: np.ndarray
    next_priv: np.ndarray
    mask: np.ndarray
    info: list[dict[str, Any]]

    @property
    def length(self) -> int:
        return int(self.obs.shape[0])


class SequenceReplayBuffer:
    """Simple CPU sequence replay buffer for recurrent off-policy training.

    Stores rollout fragments. Sampling returns padded fixed-length sequences.
    This is intentionally lightweight and dependency-free; enough for TSC where
    environment sampling dominates wall-clock.
    """

    def __init__(self, capacity_fragments: int, seed: int = 0):
        self.capacity_fragments = int(capacity_fragments)
        self.rng = random.Random(int(seed))
        self.fragments: deque[Fragment] = deque(maxlen=self.capacity_fragments)
        self.num_transitions = 0
        self.num_fragments_added = 0

    def __len__(self) -> int:
        return len(self.fragments)

    def add_fragment(self, frag: Fragment) -> None:
        if len(self.fragments) == self.capacity_fragments:
            old = self.fragments[0]
            self.num_transitions -= int(old.mask.sum())
        self.fragments.append(frag)
        self.num_transitions += int(frag.mask.sum())
        self.num_fragments_added += 1

    def add_from_dict(self, data: dict[str, Any]) -> None:
        frag = Fragment(
            obs=np.asarray(data["obs"], dtype=np.float32),
            priv=np.asarray(data["priv"], dtype=np.float32),
            action=np.asarray(data["action"], dtype=np.float32),
            reward=np.asarray(data["reward"], dtype=np.float32),
            done=np.asarray(data["done"], dtype=np.float32),
            cost=np.asarray(data.get("cost", np.zeros((np.asarray(data["reward"]).shape[0], 0), dtype=np.float32)), dtype=np.float32),
            next_obs=np.asarray(data["next_obs"], dtype=np.float32),
            next_priv=np.asarray(data["next_priv"], dtype=np.float32),
            mask=np.asarray(data.get("mask", np.ones_like(data["reward"])), dtype=np.float32),
            info=list(data.get("info", [])),
        )
        self.add_fragment(frag)

    def can_sample(self, batch_size: int, seq_len: int) -> bool:
        return len(self.fragments) >= max(1, int(batch_size) // 4) and self.num_transitions >= int(batch_size) * int(seq_len)

    def sample(self, batch_size: int, seq_len: int) -> dict[str, np.ndarray]:
        if not self.fragments:
            raise RuntimeError("replay buffer is empty")
        batch_size = int(batch_size)
        seq_len = int(seq_len)
        obs_list = []
        priv_list = []
        act_list = []
        rew_list = []
        done_list = []
        cost_list = []
        nobs_list = []
        npriv_list = []
        mask_list = []

        for _ in range(batch_size):
            frag = self.rng.choice(tuple(self.fragments))
            L = frag.length
            if L >= seq_len:
                start = self.rng.randint(0, L - seq_len)
                sl = slice(start, start + seq_len)
                obs = frag.obs[sl]
                priv = frag.priv[sl]
                act = frag.action[sl]
                rew = frag.reward[sl]
                done = frag.done[sl]
                cost = frag.cost[sl] if frag.cost.ndim == 2 else np.zeros((rew.shape[0], 0), dtype=np.float32)
                nobs = frag.next_obs[sl]
                npriv = frag.next_priv[sl]
                mask = frag.mask[sl]
            else:
                pad = seq_len - L
                obs = np.pad(frag.obs, ((0, pad), (0, 0)), mode="constant")
                priv = np.pad(frag.priv, ((0, pad), (0, 0)), mode="constant")
                act = np.pad(frag.action, ((0, pad), (0, 0)), mode="constant")
                rew = np.pad(frag.reward, (0, pad), mode="constant")
                done = np.pad(frag.done, (0, pad), mode="constant", constant_values=1.0)
                if frag.cost.ndim == 2 and frag.cost.shape[1] > 0:
                    cost = np.pad(frag.cost, ((0, pad), (0, 0)), mode="constant")
                else:
                    cost = np.zeros((seq_len, 0), dtype=np.float32)
                nobs = np.pad(frag.next_obs, ((0, pad), (0, 0)), mode="constant")
                npriv = np.pad(frag.next_priv, ((0, pad), (0, 0)), mode="constant")
                mask = np.pad(frag.mask, (0, pad), mode="constant")
            obs_list.append(obs)
            priv_list.append(priv)
            act_list.append(act)
            rew_list.append(rew)
            done_list.append(done)
            cost_list.append(cost)
            nobs_list.append(nobs)
            npriv_list.append(npriv)
            mask_list.append(mask)

        return {
            "obs": np.stack(obs_list).astype(np.float32),
            "priv": np.stack(priv_list).astype(np.float32),
            "action": np.stack(act_list).astype(np.float32),
            "reward": np.stack(rew_list).astype(np.float32),
            "done": np.stack(done_list).astype(np.float32),
            "cost": np.stack(cost_list).astype(np.float32),
            "next_obs": np.stack(nobs_list).astype(np.float32),
            "next_priv": np.stack(npriv_list).astype(np.float32),
            "mask": np.stack(mask_list).astype(np.float32),
        }

    def stats(self) -> dict[str, int]:
        return {
            "fragments": len(self.fragments),
            "transitions": int(self.num_transitions),
            "fragments_added_lifetime": int(self.num_fragments_added),
            "capacity_fragments": int(self.capacity_fragments),
        }
