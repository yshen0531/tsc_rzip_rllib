from __future__ import annotations

import copy
from decimal import Decimal
import inspect
import json
import math
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
    stage4_2r3c3t13s14_active_calibration_sentinel as s14,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s14_active_calibration_sentinel_370ms.json"


class Stage42R3C3T13S14Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_self_test_and_count_arithmetic(self):
        s14._validate_config(self.cfg)
        result = s14._self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(result["esn_candidate_count"], 54)
        self.assertEqual(result["kernel_candidate_count"], 12)
        self.assertEqual(result["event_arithmetic"], {
            "calibration_pairs": 576, "calibration_events": 1152,
            "zero_net_groups": 704, "response_events": 256,
        })

    def _source_table(self):
        rows = []
        for pair in self.cfg["selection"]["pair_ids"]:
            for member in self.cfg["selection"]["history_members"]:
                rows.append({
                    "pair_id": pair, "history_member": member,
                    "partition": "training", "consumed_training": False,
                    "target_id": "wrong", "action_delay_steps": 99, "slew_scale": 9.9,
                    "state_generation_experiment_id": f"state_{pair}_{member}",
                    "restart_snapshot_dir": f"snapshot/{pair}/{member}",
                    "restart_snapshot_manifest_digest": f"digest_{pair}_{member}",
                })
        return rows

    def test_context_selection_is_factor_only_and_cyclic(self):
        ctx = SimpleNamespace(cfg=self.cfg, base_ctx=object())
        with mock.patch.object(s14.s13, "build_context_table", return_value=self._source_table()):
            table = s14.build_context_table(ctx)
        self.assertEqual(len(table), 16)
        by_pair = {}
        for row in table:
            by_pair.setdefault(row["pair_id"], set()).add(row["regime_id"])
        self.assertEqual([next(iter(by_pair[pair])) for pair in sorted(by_pair)], list("ABCDABCD"))
        self.assertTrue(all(row["partition"] == "sentinel" for row in table))

    def test_spec_matrix_is_16_plus_128_and_keeps_formal_horizon(self):
        ctx = SimpleNamespace(cfg=self.cfg, base_ctx=object())
        with mock.patch.object(s14.s13, "build_context_table", return_value=self._source_table()):
            table = s14.build_context_table(ctx)
        templates = {}
        for target in ("nominal", "RZ_p10_m10"):
            for delay, slew in ((0, 1.0), (2, 0.9)):
                templates[(target, delay, slew)] = {
                    "target_id": target, "action_delay_steps": delay, "slew_scale": slew,
                    "target_R_offset_m": 0.0 if target == "nominal" else 0.01,
                    "target_Z_offset_m": 0.0 if target == "nominal" else -0.01,
                    "target_Ip_offset_A": 0.0,
                }
        with mock.patch.object(s14.s13, "_source_templates", return_value=templates):
            specs = s14.build_specs(ctx, table)
        self.assertEqual(len(specs), 144)
        self.assertEqual(len(s14._baseline_specs(specs)), 16)
        self.assertEqual(len(s14._probe_specs(specs)), 128)
        self.assertEqual({row["r3c3_probe_issue_step"] for row in s14._probe_specs(specs)}, {10})
        self.assertEqual({row["r3c3_probe_cancel_step"] for row in s14._probe_specs(specs)}, {11})
        self.assertEqual({row["horizon_steps"] for row in specs}, {35, 37})
        self.assertTrue(all(row["formal_horizon_steps"] == row["horizon_steps"] for row in specs))

    def test_controller_projection_removes_pair_and_history_labels(self):
        spec = {
            "pair_id": "secret_pair", "history_member": "secret_history",
            "state_generation_experiment_id": "secret_state",
            "restart_snapshot_dir": "secret_snapshot",
            "restart_snapshot_manifest_digest": "secret_digest",
        }
        projected = s14.s9._controller_spec(spec)
        self.assertNotIn("pair_id", projected)
        self.assertNotIn("history_member", projected)
        self.assertNotIn("state_generation_experiment_id", projected)

    def test_calibration_trace_requires_four_exact_pairs(self):
        trace = [{} for _ in range(12)]
        for index, (issue, cancel, direction) in enumerate(zip((0, 2, 4, 6), (1, 3, 5, 7), s14.DIRECTIONS)):
            fields = [f"{index}.00000000"] * 14
            trace[issue] = {
                "r3c3t13s14_lattice_event": "calibration_issue",
                "r3c3t13s14_event_index": index,
                "r3c3t13s14_event_direction": direction,
                "r3c3t13s14_lattice": {"positive_target_fields": fields},
                "r3c3t13s9_actuator_prediction": {"card15_fields": fields},
                "r3c3t13s14_requested_net_kAt_tsc": [0.0] * 14,
            }
            trace[cancel] = {
                "r3c3t13s14_lattice_event": "calibration_cancel",
                "r3c3t13s14_event_index": index,
                "r3c3t13s14_event_direction": direction,
                "r3c3t13s14_lattice": {
                    "target_fields": fields, "selected_method": "exact_return_to_stored_issue_center",
                    "passed": True,
                },
                "r3c3t13s9_actuator_prediction": {"card15_fields": fields},
                "r3c3t13s14_requested_net_kAt_tsc": [0.0] * 14,
            }
        audit = s14._calibration_trace_audit({"controller_trace": trace})
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["issue_cancel_trace_event_count"], 8)
        broken = copy.deepcopy(trace)
        broken[3]["r3c3t13s14_event_direction"] = "mode2"
        self.assertFalse(s14._calibration_trace_audit({"controller_trace": broken})["passed"])

    def test_nearest_count_repairs_card15_rounding_without_weakening_symmetry(self):
        count, plus, minus = s14._nearest_exact_symmetric_count(
            Decimal("-0.9991"), Decimal("0.0001"), 150
        )
        self.assertEqual(count, 149)
        center = Decimal("-0.9991")
        self.assertEqual(s14.s9._decimal_field(plus) - center, center - s14.s9._decimal_field(minus))
        self.assertEqual(s14.s9._decimal_field(plus), center + Decimal("0.0001") * count)
        self.assertEqual(s14.s9._decimal_field(minus), center - Decimal("0.0001") * count)

    def test_runtime_hotfix_manifest_compatibility_is_narrow(self):
        module = "tsc_rzip_rllib/diagnostics/stage4_2r3c3t13s14_active_calibration_sentinel.py"
        old = {
            "identity": "unchanged",
            "deployed_package_fingerprint": {
                "contract": "r42r3c3t13s14_deployed_package_source_v1",
                "package_revision": s14.PACKAGE_REVISION,
                "digest": "old", "files": [
                    {"path": module, "size_bytes": 1, "sha256": "old"}
                ],
            },
        }
        new = copy.deepcopy(old)
        new["deployed_package_fingerprint"].update({
            "digest": "new", "files": [
                {"path": module, "size_bytes": 2, "sha256": "new"}
            ],
        })
        compatible, changed = s14._runtime_hotfix_manifest_compatible(old, new)
        self.assertTrue(compatible)
        self.assertEqual([row["path"] for row in changed], [module])
        new["deployed_package_fingerprint"]["files"][0]["path"] = "configs/changed.json"
        self.assertFalse(s14._runtime_hotfix_manifest_compatible(old, new)[0])

    def test_response_count_repair_is_scoped_without_global_monkeypatch(self):
        action_source = inspect.getsource(s14.ActiveCalibrationProbeController.action)
        response_source = inspect.getsource(
            s14.ActiveCalibrationProbeController._response_lattice_action
        )
        self.assertIn("task_step in {self.issue_step, self.cancel_step}", action_source)
        self.assertIn("inherited_action, trace = super().action", action_source)
        self.assertIn("_choose_exact_symmetric_displacement", response_source)
        self.assertIn(
            "AuthenticatedVisibleManifoldPhaseTaskController.action", response_source
        )
        self.assertNotIn("s9.choose_lattice_displacement =", response_source)

    def test_pre_response_exact_ignores_only_wallclock_fields(self):
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
        audit = s14._pre_response_semantic_exact(probe, baseline)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["semantic_state_mismatch_count"], 0)
        self.assertEqual(audit["action_prefix_mismatch_count"], 0)
        self.assertEqual(audit["excluded_timing_difference_count"], 22)
        probe["trajectory"][3]["R"] = 1.1
        self.assertFalse(s14._pre_response_semantic_exact(probe, baseline)["passed"])

    def test_kernel_prediction_is_exactly_zero_at_zero_action(self):
        model = {
            "family": "kernel", "bandwidth": 1.0,
            "training_histories": [np.zeros(1020).tolist(), np.ones(1020).tolist()],
            "training_action_coordinates": [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
            "action_basis": np.eye(14)[:4].tolist(), "action_rms": [1.0] * 4,
            "alpha": np.ones((2, 5)).tolist(),
        }
        row = {"padded_history": np.zeros(1020), "u_center": np.zeros(14)}
        predicted, derivative = s14._predict_kernel(row, model, self.cfg["observer"])
        np.testing.assert_array_equal(predicted, np.zeros(5))
        self.assertEqual(derivative.shape, (14, 5))

    def _model_rows(self):
        rows = []
        directions = list(s14.DIRECTIONS)
        for pair_index in range(8):
            for member_index, member in enumerate(("plus_first", "minus_first")):
                for direction_index, direction in enumerate(directions):
                    for sign in s14.SIGNS:
                        output = np.asarray([1e-4, 1e-4, 1e-3, 1e-3, 10.0]) * sign
                        rows.append({
                            "pair_id": f"pair_{pair_index}", "history_member": member,
                            "window": "active_response", "direction": direction, "sign": sign,
                            "sequence": np.zeros((11, 59)),
                            "padded_history": np.full(1020, pair_index + 0.1 * member_index),
                            "u_center": np.eye(14)[direction_index] * sign,
                            "u_radius": np.zeros(14), "output": output,
                        })
        return rows

    def test_whole_pair_cv_holds_both_histories_and_all_directions(self):
        rows = self._model_rows()
        model = {"family": "esn", "eligible": True, "interaction_condition": 1.0}
        with mock.patch.object(s14, "_fit_family", return_value=model), mock.patch.object(
            s14, "_predict_family", side_effect=lambda row, _model, _cfg: (
                np.asarray(row["output"]), np.zeros((14, 5))
            ),
        ):
            audit = s14._cross_validate_candidate(
                rows,
                {"family": "esn", "rho": 0.35, "leak": 0.5, "observer_rank": 4, "ridge": 1e-8},
                self.cfg["observer"],
            )
        self.assertTrue(audit["eligible"])
        self.assertEqual(len(audit["folds"]), 8)
        self.assertTrue(all(row["held_row_count"] == 16 for row in audit["folds"]))
        self.assertEqual(audit["held_row_count"], 128)

    def test_structurally_ineligible_candidate_uses_strict_json_nulls(self):
        rows = self._model_rows()
        model = {
            "family": "kernel", "eligible": False,
            "interaction_condition": math.inf, "failure_reason": "ill conditioned",
        }
        with mock.patch.object(s14, "_fit_family", return_value=model):
            audit = s14._cross_validate_candidate(
                rows,
                {"family": "kernel", "bandwidth_multiplier": 0.5, "ridge": 1e-8},
                self.cfg["observer"],
            )
        self.assertFalse(audit["eligible"])
        self.assertIsNone(audit["maximum_error"])
        self.assertIsNone(audit["mean_error"])
        self.assertIsNone(audit["maximum_condition"])
        self.assertTrue(all(row["condition"] is None for row in audit["folds"]))
        json.dumps(audit, allow_nan=False)

    def test_history_signature_fails_near_alias(self):
        rows = self._model_rows()
        with mock.patch.object(s14.s13, "_identification_gates", return_value={"passed": True}):
            audit = s14._identification_gates(rows, SimpleNamespace(cfg=self.cfg))
        self.assertTrue(audit["passed"])
        for row in rows:
            if row["pair_id"] == "pair_0":
                row["padded_history"] = np.zeros(1020)
        with mock.patch.object(s14.s13, "_identification_gates", return_value={"passed": True}):
            audit = s14._identification_gates(rows, SimpleNamespace(cfg=self.cfg))
        self.assertFalse(audit["passed"])

    def test_stop_launcher_never_broadly_kills_processes(self):
        text = (ROOT / "run_stop_stage4_2r3c3t13s14_now.sh").read_text(encoding="utf-8")
        self.assertNotIn("pkill", text)
        self.assertNotIn("ray stop --force", text)
        self.assertIn("kill -TERM", text)


if __name__ == "__main__":
    unittest.main()
