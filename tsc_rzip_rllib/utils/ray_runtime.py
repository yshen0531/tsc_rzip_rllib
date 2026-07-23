"""Ray capacity planning for variable-size real-TSC evaluation waves.

The diagnostic pipeline executes several Ray waves with different candidate
counts (for example 84, 24, 48, 120, 150, and 99).  A local Ray instance must
therefore be initialized with the *configured campaign capacity*, not with the
size of the first wave.  Initializing from the first wave silently under-sizes
Ray and can leave later actors permanently unschedulable.

This module has no top-level Ray dependency so unit tests can exercise the
planning logic without importing Ray.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RayWorkerPlan:
    """Resolved Ray capacity and actor count for one evaluation wave."""

    requested_workers: int
    cluster_cpus: int
    pending_tasks: int
    actor_count: int
    initialized_now: bool

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "requested_workers": self.requested_workers,
            "cluster_cpus": self.cluster_cpus,
            "pending_tasks": self.pending_tasks,
            "actor_count": self.actor_count,
            "initialized_now": self.initialized_now,
        }


def _positive_int(name: str, value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc
    if parsed < 1:
        raise ValueError(f"{name} must be >= 1, got {parsed}")
    return parsed


def _cluster_cpu_count(ray_module: Any) -> int:
    resources = ray_module.cluster_resources()
    raw = float(resources.get("CPU", 0.0))
    if not math.isfinite(raw) or raw < 1.0:
        raise RuntimeError(
            "Ray reported no usable CPU resource after initialization: "
            f"cluster_resources={resources!r}"
        )
    # Ray resources are represented as floats.  CPU resources used here are
    # integral because every evaluator actor declares num_cpus=1.
    return max(1, int(math.floor(raw + 1e-9)))


def ensure_ray_worker_plan(
    ray_module: Any,
    *,
    requested_workers: int,
    pending_tasks: int,
    ray_tmpdir: str | None,
    log_prefix: str,
) -> RayWorkerPlan:
    """Initialize/validate Ray and return the safe actor count for a wave.

    The key invariant is that the local Ray instance is initialized with
    ``requested_workers`` even when the first wave has fewer tasks.  If the
    process is already attached to a smaller Ray cluster, fail immediately
    rather than enqueue actors that can never be scheduled.
    """

    requested = _positive_int("requested_workers", requested_workers)
    pending = _positive_int("pending_tasks", pending_tasks)
    initialized_now = False

    if not ray_module.is_initialized():
        ray_module.init(
            num_cpus=requested,
            include_dashboard=False,
            ignore_reinit_error=True,
            _temp_dir=ray_tmpdir,
            log_to_driver=False,
        )
        initialized_now = True

    cluster_cpus = _cluster_cpu_count(ray_module)
    if cluster_cpus < requested:
        raise RuntimeError(
            "Ray cluster is undersized for this campaign: "
            f"requested_workers={requested}, cluster_cpus={cluster_cpus}. "
            "Stop the existing Ray instance and restart through the Stage "
            "launcher so Ray is initialized at the configured capacity."
        )

    actor_count = min(requested, pending, cluster_cpus)
    plan = RayWorkerPlan(
        requested_workers=requested,
        cluster_cpus=cluster_cpus,
        pending_tasks=pending,
        actor_count=actor_count,
        initialized_now=initialized_now,
    )
    print(
        f"{log_prefix} ray_capacity "
        f"requested={requested} cluster_cpus={cluster_cpus} "
        f"pending={pending} actors={actor_count} "
        f"initialized_now={int(initialized_now)}",
        flush=True,
    )
    return plan
