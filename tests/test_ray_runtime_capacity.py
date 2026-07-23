from __future__ import annotations

import inspect
import unittest

from tsc_rzip_rllib.diagnostics import stage1_controllability as s1
from tsc_rzip_rllib.diagnostics import stage2_trajectory_optimization as s2
from tsc_rzip_rllib.diagnostics import stage3_1_adaptive_sqp_mpc as s31
from tsc_rzip_rllib.diagnostics import stage3_2_margin_long_hold_mpc as s32
from tsc_rzip_rllib.utils.ray_runtime import ensure_ray_worker_plan


class FakeRay:
    def __init__(self, *, initialized: bool = False, cluster_cpus: int = 0):
        self._initialized = initialized
        self._cluster_cpus = cluster_cpus
        self.init_calls: list[dict[str, object]] = []

    def is_initialized(self) -> bool:
        return self._initialized

    def init(self, **kwargs):
        self.init_calls.append(dict(kwargs))
        self._initialized = True
        self._cluster_cpus = int(kwargs["num_cpus"])
        return {"ok": True}

    def cluster_resources(self):
        return {"CPU": float(self._cluster_cpus)}


class RayCapacityPlanningTests(unittest.TestCase):
    def test_first_small_wave_initializes_full_campaign_capacity(self) -> None:
        ray = FakeRay()
        plan = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=84,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        self.assertEqual(ray.init_calls[0]["num_cpus"], 96)
        self.assertEqual(plan.cluster_cpus, 96)
        self.assertEqual(plan.actor_count, 84)
        self.assertTrue(plan.initialized_now)

    def test_later_larger_wave_uses_all_requested_workers(self) -> None:
        ray = FakeRay()
        first = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=84,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        second = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=120,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        self.assertEqual(first.actor_count, 84)
        self.assertEqual(second.actor_count, 96)
        self.assertEqual(len(ray.init_calls), 1)
        self.assertFalse(second.initialized_now)

    def test_resume_with_twelve_pending_keeps_capacity_for_next_wave(self) -> None:
        ray = FakeRay()
        resumed = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=12,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        proposal = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=24,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        identification = ensure_ray_worker_plan(
            ray,
            requested_workers=96,
            pending_tasks=150,
            ray_tmpdir="/tmp/test_ray",
            log_prefix="[test]",
        )
        self.assertEqual(resumed.actor_count, 12)
        self.assertEqual(proposal.actor_count, 24)
        self.assertEqual(identification.actor_count, 96)
        self.assertEqual(ray.init_calls[0]["num_cpus"], 96)
        self.assertEqual(len(ray.init_calls), 1)

    def test_existing_undersized_cluster_fails_fast(self) -> None:
        ray = FakeRay(initialized=True, cluster_cpus=84)
        with self.assertRaisesRegex(RuntimeError, "undersized"):
            ensure_ray_worker_plan(
                ray,
                requested_workers=96,
                pending_tasks=120,
                ray_tmpdir="/tmp/test_ray",
                log_prefix="[test]",
            )

    def test_invalid_counts_are_rejected(self) -> None:
        ray = FakeRay()
        with self.assertRaises(ValueError):
            ensure_ray_worker_plan(
                ray,
                requested_workers=0,
                pending_tasks=1,
                ray_tmpdir=None,
                log_prefix="[test]",
            )
        with self.assertRaises(ValueError):
            ensure_ray_worker_plan(
                ray,
                requested_workers=1,
                pending_tasks=0,
                ray_tmpdir=None,
                log_prefix="[test]",
            )

    def test_open_loop_evaluator_uses_capacity_helper(self) -> None:
        source = inspect.getsource(s2.evaluate_specs)
        self.assertIn("ensure_ray_worker_plan", source)
        self.assertNotIn("num_cpus=n_workers", source)

    def test_feedback_and_stage1_paths_use_capacity_helper(self) -> None:
        for function in (
            s31.evaluate_feedback_specs,
            s32.evaluate_feedback_specs,
            s1.run_scan,
            s1.run_validation,
        ):
            source = inspect.getsource(function)
            self.assertIn("ensure_ray_worker_plan", source, function.__name__)
            self.assertNotIn("num_cpus=n_workers", source, function.__name__)


if __name__ == "__main__":
    unittest.main()
