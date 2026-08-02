from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import sys
import types
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

if sys.platform == "win32":
    try:
        import resource as _resource  # type: ignore[import-not-found]  # noqa: F401
    except ModuleNotFoundError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.getrlimit = lambda _kind: (1024, 4096)
        resource.setrlimit = lambda _kind, _limits: None
        sys.modules["resource"] = resource

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s15_fixed_basis_local_identification as s15,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s15_fixed_basis_local_identification_370ms.json"


class Stage42R3C3T13S15Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_local_design(self):
        s15._validate_config(self.cfg)
        result = s15._self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(result["local_design_rank"], 7)
        self.assertLess(result["local_design_condition"], 3.0)
        self.assertAlmostEqual(result["local_design_condition"], 2.529381, places=5)
        self.assertEqual(result["event_arithmetic"], {
            "calibration_pairs": 576, "calibration_events": 1152,
            "zero_net_groups": 704, "response_events": 256,
        })

    def _source_table(self):
        return [
            {
                "pair_id": pair, "history_member": member,
                "partition": "training", "consumed_training": False,
                "target_id": "wrong", "action_delay_steps": 99, "slew_scale": 9.9,
                "state_generation_experiment_id": f"state_{pair}_{member}",
                "restart_snapshot_dir": f"snapshot/{pair}/{member}",
                "restart_snapshot_manifest_digest": f"digest_{pair}_{member}",
            }
            for pair in self.cfg["selection"]["pair_ids"]
            for member in self.cfg["selection"]["history_members"]
        ]

    def test_factor_selection_and_spec_matrix_are_frozen(self):
        ctx = SimpleNamespace(cfg=self.cfg, base_ctx=object())
        with mock.patch.object(s15.s13, "build_context_table", return_value=self._source_table()):
            table = s15.build_context_table(ctx)
        templates = {}
        for target in ("nominal", "RZ_p10_m10"):
            for delay, slew in ((0, 1.0), (2, 0.9)):
                templates[(target, delay, slew)] = {
                    "target_id": target, "action_delay_steps": delay, "slew_scale": slew,
                    "target_R_offset_m": 0.0, "target_Z_offset_m": 0.0,
                    "target_Ip_offset_A": 0.0,
                }
        with mock.patch.object(s15.s13, "_source_templates", return_value=templates):
            specs = s15.build_specs(ctx, table)
        self.assertEqual(len(table), 16)
        self.assertEqual(len(specs), 144)
        self.assertEqual(len(s15._baseline_specs(specs)), 16)
        self.assertEqual(len(s15._probe_specs(specs)), 128)
        self.assertEqual({row["horizon_steps"] for row in specs}, {35, 37})
        self.assertTrue(all(row["formal_horizon_steps"] == row["horizon_steps"] for row in specs))

    def _exact_trace(self):
        basis = np.eye(14, dtype=float)[:4].tolist()
        trace = [
            {"r3c3t13s15_fixed_basis_delta_field_kAt_tsc": copy.deepcopy(basis)}
            for _ in range(12)
        ]
        for index, (issue, cancel, direction) in enumerate(
            zip((0, 2, 4, 6), (1, 3, 5, 7), s15.DIRECTIONS)
        ):
            fields = [f"{index}.00000000"] * 14
            delta = basis[index]
            trace[issue].update({
                "r3c3t13s15_lattice_event": "calibration_issue",
                "r3c3t13s15_event_index": index,
                "r3c3t13s15_event_direction": direction,
                "r3c3t13s15_lattice": {
                    "positive_target_fields": fields,
                    "selected_method": "exact_fixed_signed_increment_relative_current_center",
                    "fixed_sign": 1, "fixed_delta_field_kAt_tsc": delta,
                    "signed_delta_field_kAt_tsc": delta, "passed": True,
                },
                "r3c3t13s9_actuator_prediction": {"card15_fields": fields},
                "r3c3t13s15_requested_net_kAt_tsc": [0.0] * 14,
            })
            trace[cancel].update({
                "r3c3t13s15_lattice_event": "calibration_cancel",
                "r3c3t13s15_event_index": index,
                "r3c3t13s15_event_direction": direction,
                "r3c3t13s15_lattice": {
                    "target_fields": fields,
                    "selected_method": "exact_fixed_signed_increment_relative_current_center",
                    "fixed_sign": -1, "fixed_delta_field_kAt_tsc": delta,
                    "signed_delta_field_kAt_tsc": (-np.asarray(delta)).tolist(),
                    "passed": True,
                },
                "r3c3t13s9_actuator_prediction": {"card15_fields": fields},
                "r3c3t13s15_requested_net_kAt_tsc": [0.0] * 14,
            })
        return trace

    def test_calibration_trace_requires_constant_rank4_exact_signed_pairs(self):
        trace = self._exact_trace()
        audit = s15._calibration_trace_audit({"controller_trace": trace})
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["fixed_basis_rank"], 4)
        self.assertEqual(audit["fixed_basis_normalized_condition"], 1.0)
        broken = copy.deepcopy(trace)
        broken[7]["r3c3t13s15_lattice"]["signed_delta_field_kAt_tsc"][3] = -2.0
        self.assertFalse(s15._calibration_trace_audit({"controller_trace": broken})["passed"])
        drifting = copy.deepcopy(trace)
        drifting[4]["r3c3t13s15_fixed_basis_delta_field_kAt_tsc"][0][0] = 2.0
        self.assertFalse(s15._calibration_trace_audit({"controller_trace": drifting})["passed"])

    def test_controller_freezes_once_and_uses_contemporaneous_centers(self):
        freeze_source = inspect.getsource(s15.FixedBasisLocalProbeController._freeze_fixed_basis)
        signed_source = inspect.getsource(s15.FixedBasisLocalProbeController._fixed_signed_calibration)
        self.assertIn("if self._fixed_basis_delta", freeze_source)
        self.assertIn("center = self.actuator.apply(currents, baseline_action)", signed_source)
        self.assertIn("center_value + sign * value", signed_source)
        self.assertNotIn("_issue_center_fields", signed_source)
        self.assertNotIn("pair_id", signed_source)
        self.assertNotIn("history_member", signed_source)

    def test_resume_requires_exact_manifest(self):
        old = {"identity": "frozen", "package": {"digest": "same"}}
        self.assertTrue(s15._resume_manifest_exact(old, copy.deepcopy(old)))
        changed = copy.deepcopy(old)
        changed["package"]["digest"] = "changed"
        self.assertFalse(s15._resume_manifest_exact(old, changed))

    def _synthetic_local_case(self):
        design = s15._local_design(self.cfg["observer"])
        beta = np.zeros((7, 5), dtype=float)
        beta[0] = [1.7, 0.1, 0.0, 0.0, 800000.0]
        beta[1] = [1e-3, -1e-3, 1e-2, -1e-2, 50.0]
        beta[2] = [2e-4, 2e-4, 2e-3, 2e-3, 20.0]
        beta[3:7] = np.asarray([
            [1e-4, 2e-4, 1e-3, 2e-3, 10.0],
            [2e-4, 1e-4, 2e-3, 1e-3, 20.0],
            [-1e-4, 1e-4, -1e-3, 1e-3, -10.0],
            [1.5e-4, -1e-4, 1.5e-3, -1e-3, 15.0],
        ])
        outputs = design @ beta
        basis = np.eye(14, dtype=float)[:4].tolist()
        trace = [
            {"r3c3t13s15_fixed_basis_delta_field_kAt_tsc": copy.deepcopy(basis)}
            for _ in range(11)
        ]
        trace[10]["r3c3t13s9_signed_issue_delta_kAt_tsc"] = basis[2]
        result = {
            "experiment_id": "synthetic", "controller_trace": trace,
            "spec": {
                "pair_id": "pair", "history_member": "plus_first",
                "r3c3_probe_direction": "mode1", "r3c3_probe_sign": 1,
            },
        }
        response = {
            "u_radius": np.zeros(14), "output": beta[5].copy(),
        }
        return outputs, result, response

    def test_local_estimator_recovers_exact_causal_response(self):
        outputs, result, response = self._synthetic_local_case()
        with mock.patch.object(s15, "_visible_local_outputs", return_value=outputs), \
             mock.patch.object(s15.s13, "_turns_tsc", return_value=np.full(14, 1000.0)), \
             mock.patch.object(s15.s13, "_current_scales", return_value=np.ones(14)):
            audit = s15._local_response_row(
                result=result, response=response, payload={},
                observer_cfg=self.cfg["observer"],
            )
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["design_rank"], 7)
        self.assertEqual(audit["fixed_basis_rank"], 4)
        self.assertAlmostEqual(audit["response_basis_cosine"], 1.0)
        self.assertLess(audit["maximum_scaled_center_relative_error"], 1e-10)

    def test_local_estimator_rejects_real_center_error(self):
        outputs, result, response = self._synthetic_local_case()
        response["output"] = np.asarray(response["output"]) + [0.01, 0, 0, 0, 0]
        with mock.patch.object(s15, "_visible_local_outputs", return_value=outputs), \
             mock.patch.object(s15.s13, "_turns_tsc", return_value=np.full(14, 1000.0)), \
             mock.patch.object(s15.s13, "_current_scales", return_value=np.ones(14)):
            audit = s15._local_response_row(
                result=result, response=response, payload={},
                observer_cfg=self.cfg["observer"],
            )
        self.assertFalse(audit["center_pass"])
        self.assertFalse(audit["passed"])

    def test_pre_response_comparison_ignores_only_wallclock(self):
        baseline = {
            "trajectory": [
                {"R": 1.0, "Z": 2.0, "gotsc_subprocess_s": 1.0, "step_total_s": 2.0}
                for _ in range(11)
            ],
            "controller_trace": [{"action_norm_tsc": [0.0] * 14} for _ in range(10)],
        }
        probe = copy.deepcopy(baseline)
        for row in probe["trajectory"]:
            row["gotsc_subprocess_s"] = 30.0
            row["step_total_s"] = 31.0
        self.assertTrue(s15._pre_response_semantic_exact(probe, baseline)["passed"])
        probe["trajectory"][3]["R"] = 1.1
        self.assertFalse(s15._pre_response_semantic_exact(probe, baseline)["passed"])

    def test_stop_launcher_never_broadly_kills_processes(self):
        text = (ROOT / "run_stop_stage4_2r3c3t13s15_now.sh").read_text(encoding="utf-8")
        self.assertNotIn("pkill", text)
        self.assertNotIn("ray stop --force", text)
        self.assertIn("kill -TERM", text)


if __name__ == "__main__":
    unittest.main()
