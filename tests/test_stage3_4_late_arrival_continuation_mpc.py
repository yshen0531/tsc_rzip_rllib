from __future__ import annotations

import copy
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from tsc_rzip_rllib.diagnostics import stage3_4_late_arrival_continuation_mpc as s34


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage3_4_late_arrival_continuation_mpc_350ms.json"


def fake_context():
    cfg = json.loads(CONFIG.read_text())
    env = {
        "dt_ms": 10,
        "min_current_a_display_order": [-1e6] * 14,
        "max_current_a_display_order": [1e6] * 14,
    }
    return SimpleNamespace(
        cfg=cfg,
        env_cfg=env,
        modes_tsc=np.eye(14, 3),
        initial_currents_tsc=np.zeros(14),
        max_delta_a=3.0,
        min_current_tsc=np.full(14, -1e6),
        max_current_tsc=np.full(14, 1e6),
    )


def trajectory_for_errors(errors_r, errors_z, ip_error=0.0):
    rows = []
    for step, (r, z) in enumerate(zip(errors_r, errors_z)):
        rows.append(
            {
                "R": 0.75 + r,
                "Z": z,
                "Ip": 29779.724 + ip_error,
                "currents_a_display": [0.0] * 14,
                "currents_a_tsc": [0.0] * 14,
                "abnormal": False,
            }
        )
    return {"success": True, "trajectory": rows, "wall_time_s": 1.0}


class Stage34Tests(unittest.TestCase):
    def test_config_and_continuation_order(self):
        cfg = json.loads(CONFIG.read_text())
        s34.validate_stage34_config(cfg)
        tasks = s34.build_tasks(cfg)
        self.assertEqual(len(tasks), 16)
        self.assertEqual(sum(t["final"] and t["mandatory"] for t in tasks), 10)
        seen = set()
        for task in tasks:
            self.assertTrue(set(task["parents"]).issubset(seen))
            seen.add(task["task_id"])

    def test_latest_arrival_250ms_still_requires_hold_to_350ms(self):
        ctx = fake_context()
        task = s34.build_tasks(ctx.cfg)[0]
        # States 23..35 are inside, so endpoint 25 has its three-state arrival
        # window and then ten further control intervals of hold.
        # Keep state 22 just outside the box so endpoint 240 ms fails, then
        # enter gently enough that endpoint 250 ms also satisfies its 4-step
        # late-velocity RMS check.  States 23..35 remain inside through 350 ms.
        r = [0.05] * 20 + [0.035, 0.0315, 0.0305, 0.0300] + [0.0295] * 12
        z = [0.018] * 36
        metrics = s34.target_metrics(ctx, task, trajectory_for_errors(r, z), None)
        self.assertTrue(metrics["stage3_4_target_tracking_pass"])
        self.assertEqual(metrics["stage3_4_best_endpoint_ms"], 250)

    def test_arrival_after_250ms_does_not_pass(self):
        ctx = fake_context()
        task = s34.build_tasks(ctx.cfg)[0]
        r = [0.05] * 26 + [0.020] * 10
        z = [0.05] * 26 + [0.018] * 10
        metrics = s34.target_metrics(ctx, task, trajectory_for_errors(r, z), None)
        self.assertFalse(metrics["stage3_4_target_tracking_pass"])

    def test_tail_extension_and_clip(self):
        ctx = fake_context()
        vector = np.zeros(75)
        vector[-3:] = [0.2, -0.1, 0.03]
        for template in ctx.cfg["continuation"]["tail_templates"]:
            full = s34.extend_25_to_35(ctx, vector, template)
            self.assertEqual(full.shape, (105,))
            self.assertTrue(np.all(np.isfinite(full)))

    def test_reduced_basis_rank(self):
        ctx = fake_context()
        basis = s34.temporal_reduced_basis(ctx)
        self.assertEqual(basis.shape, (105, 18))
        self.assertEqual(np.linalg.matrix_rank(basis), 18)

    def test_physical_digest_ignores_target(self):
        vector = np.linspace(-0.2, 0.2, 105)
        self.assertEqual(s34.physical_digest(vector), s34.physical_digest(vector.copy()))
        self.assertNotEqual(
            s34.candidate_digest("target_a", vector),
            s34.candidate_digest("target_b", vector),
        )

    def test_dynamic_mpc_indices(self):
        self.assertEqual(len(s34._future_control_columns(0)), 105)
        self.assertEqual(len(s34._future_control_columns(34)), 3)
        self.assertEqual(len(s34._future_feature_rows(0)), 175)
        self.assertEqual(len(s34._future_feature_rows(34)), 5)




    def test_internal_margin_goal_is_stricter_than_hard_pass(self):
        ctx = fake_context()
        nominal = s34.build_tasks(ctx.cfg)[0]
        thin = {
            "stage3_4_target_tracking_pass": True,
            "stage3_4_sustained_box_max_error_m": 0.029,
            "stage3_4_post_arrival_velocity_rms_m_per_s": 0.05,
        }
        centered = {
            "stage3_4_target_tracking_pass": True,
            "stage3_4_sustained_box_max_error_m": 0.019,
            "stage3_4_post_arrival_velocity_rms_m_per_s": 0.05,
        }
        self.assertFalse(s34.task_internal_goal(ctx, nominal, thin))
        self.assertTrue(s34.task_internal_goal(ctx, nominal, centered))
        self.assertEqual(s34.task_minimum_refinement_rounds(ctx, nominal), 2)

    def test_global_physical_cache_is_reused_even_for_fresh_phase(self):
        ctx = fake_context()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ctx.paths = SimpleNamespace(physical_cache=root / "cache", run_dir=root)
            ctx.base32 = object()
            task = s34.build_tasks(ctx.cfg)[0]
            row = {
                "task": task,
                "candidate_id": "logical",
                "full_control_vector": np.zeros(105).tolist(),
                "source_name": "test",
            }
            captured = {}

            def fake_evaluate(*args, **kwargs):
                captured["resume"] = kwargs["resume"]
                spec = kwargs.get("specs")
                if spec is None:
                    spec = args[1]
                return [{"experiment_id": spec[0]["experiment_id"], "success": True, "trajectory": []}]

            with mock.patch.object(s34.s2, "evaluate_specs", side_effect=fake_evaluate), mock.patch.object(
                s34,
                "target_metrics",
                return_value={
                    "success": True,
                    "stage3_4_target_tracking_pass": False,
                    "stage3_4_tracking_objective": 1.0,
                    "stage3_4_tracking_minimum_signed_margin": -1.0,
                    "stage3_4_sustained_box_max_error_m": 0.05,
                },
            ):
                s34.evaluate_task_candidates(ctx, [row], phase="fresh", backend="serial", resume=False)
            self.assertIs(captured["resume"], True)

    def test_decoder_shapes_and_finite(self):
        ctx = fake_context()
        vector = np.linspace(-0.2, 0.2, 105)
        decoded = s34.decode_control(ctx, vector)
        self.assertEqual(decoded["mode_coefficients"].shape, (35, 3))
        self.assertEqual(decoded["action_norm_tsc"].shape, (35, 14))
        self.assertEqual(decoded["action_norm_display"].shape, (35, 14))
        self.assertEqual(decoded["currents_a_tsc"].shape, (36, 14))
        self.assertTrue(np.all(np.isfinite(decoded["action_norm_tsc"])))

    def test_scale_selection_never_selects_zero_feedback(self):
        ctx = fake_context()
        rows = []
        for scenario in ("a", "b"):
            rows.extend(
                [
                    {"scenario": scenario, "controller_scale": 0.0, "stage3_4_target_tracking_pass": True, "stage3_4_tracking_minimum_signed_margin": 0.01},
                    {"scenario": scenario, "controller_scale": 0.5, "stage3_4_target_tracking_pass": True, "stage3_4_tracking_minimum_signed_margin": 0.02},
                    {"scenario": scenario, "controller_scale": 1.0, "stage3_4_target_tracking_pass": True, "stage3_4_tracking_minimum_signed_margin": 0.03},
                ]
            )
        summaries, selected = s34.scale_summaries(ctx, rows)
        self.assertTrue(all(row["controller_scale"] > 0.0 for row in summaries))
        self.assertIsNotNone(selected)
        self.assertGreater(selected["controller_scale"], 0.0)

    def test_synthetic_self_test(self):
        result = s34.synthetic_stage34_test()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["basis_shape"], [105, 18])


if __name__ == "__main__":
    unittest.main()
