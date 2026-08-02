from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s13_recurrent_sequence_tube_identification as s13,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s13_recurrent_sequence_tube_identification_370ms.json"


class Stage42R3C3T13S13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        s13._validate_config(self.cfg)
        result = s13.self_test()
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertFalse(result["bc_dagger_or_rl_allowed"])

    def test_pair_parser_is_exact(self):
        self.assertEqual(s13._parse_pair_id("p9_q2_a0p750_gap4_settle4"), (9, 2, 0.75, 4))
        with self.assertRaises(ValueError):
            s13._parse_pair_id("p9_q2_a0p750_gap5_settle4")

    def _source_rows(self):
        pairs = []
        states = []
        index = 0
        for prefix in (5, 9):
            for direction in (1, 2):
                for amplitude_text, amplitude in (("600", 0.6), ("750", 0.75), ("900", 0.9)):
                    for gap in (2, 3, 4):
                        pair = f"p{prefix}_q{direction}_a0p{amplitude_text}_gap{gap}_settle4"
                        pairs.append({"pair_id": pair, "accepted": bool(index % 2), "selected": False})
                        for member in ("plus_first", "minus_first"):
                            states.append({
                                "pair_id": pair, "history_order": member, "success": True,
                                "experiment_id": f"state_{index:03d}_{member}",
                                "snapshot_dir": str(ROOT / ".codex_tmp" / f"snapshot_{index}_{member}"),
                                "snapshot_manifest_digest": f"{index + (0 if member == 'plus_first' else 100):064x}",
                                "amplitude_fraction": amplitude,
                            })
                        index += 1
        return pairs, states

    def test_context_split_is_exhaustive_pairwise_and_ignores_acceptance(self):
        pairs, states = self._source_rows()
        pair_path = Path("pairs.json")
        state_path = Path("states.json")
        ctx = SimpleNamespace(cfg=self.cfg)
        def reader(path):
            return pairs if path == pair_path else states
        with mock.patch.object(s13, "_source_paths", return_value={"pair_results": pair_path, "state_results": state_path}), mock.patch.object(s13, "_read_json", side_effect=reader):
            table = s13.build_context_table(ctx)
        self.assertEqual(len(table), 72)
        self.assertEqual(sum(row["partition"] == "training" for row in table), 32)
        self.assertEqual(sum(row["partition"] == "calibration" for row in table), 20)
        self.assertEqual(sum(row["partition"] == "holdout" for row in table), 20)
        by_pair = {}
        for row in table:
            by_pair.setdefault(row["pair_id"], set()).add((row["partition"], row["regime_id"]))
        self.assertTrue(all(len(values) == 1 for values in by_pair.values()))
        changed = copy.deepcopy(pairs)
        for row in changed:
            row["accepted"] = not row["accepted"]
            row["selected"] = True
        def changed_reader(path):
            return changed if path == pair_path else states
        with mock.patch.object(s13, "_source_paths", return_value={"pair_results": pair_path, "state_results": state_path}), mock.patch.object(s13, "_read_json", side_effect=changed_reader):
            self.assertEqual(table, s13.build_context_table(ctx))

    def test_new_spec_matrix_has_no_partition_field_for_controller(self):
        pairs, states = self._source_rows()
        pair_path = Path("pairs.json")
        state_path = Path("states.json")
        ctx = SimpleNamespace(cfg=self.cfg)
        def reader(path):
            return pairs if path == pair_path else states
        with mock.patch.object(s13, "_source_paths", return_value={"pair_results": pair_path, "state_results": state_path}), mock.patch.object(s13, "_read_json", side_effect=reader):
            table = s13.build_context_table(ctx)
        templates = {}
        for target in ("nominal", "RZ_p10_m10"):
            for delay, slew in ((0, 1.0), (2, 0.9)):
                templates[(target, delay, slew)] = {
                    "target_id": target, "action_delay_steps": delay, "slew_scale": slew,
                    "target_R_offset_m": 0.0 if target == "nominal" else 0.01,
                    "target_Z_offset_m": 0.0 if target == "nominal" else -0.01,
                    "target_Ip_offset_A": 0.0,
                }
        with mock.patch.object(s13, "_source_templates", return_value=templates):
            specs = s13.build_new_specs(ctx, table)
        self.assertEqual(len(specs), 1088)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 1088)
        self.assertFalse(any("partition" in row for row in specs))
        self.assertEqual(sum(row["r3c3_probe_id"] == s13.BASELINE_PROBE_ID for row in specs), 64)

    @staticmethod
    def _payload():
        return {
            "cfg": {"target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0}},
            "train_cfg": {"target": {"R": 0.75, "Z": 0.0, "Ip": 30000.0}},
            "env_cfg": {
                "min_current_a_display_order": [-100.0] * 14,
                "max_current_a_display_order": [100.0] * 14,
                "turns_display_order": [10.0] * 14,
            },
        }

    @staticmethod
    def _baseline(length=18):
        trajectory = []
        trace = []
        for index in range(length):
            trajectory.append({
                "R": 0.75 + index * 1e-4, "Z": -index * 2e-4,
                "Ip": 30000.0 + index, "currents_a_tsc": [float(index)] * 14,
            })
            if index + 1 < length:
                trace.append({
                    "action_norm_tsc": [index / 100.0] * 14,
                    "issued_desired_physical_mode_coefficients": [index / 10.0] * 3,
                })
        return {
            "spec": {
                "action_delay_steps": 0, "slew_scale": 1.0,
                "target_R_offset_m": 0.01, "target_Z_offset_m": -0.01,
                "target_Ip_offset_A": 0.0,
            },
            "trajectory": trajectory, "controller_trace": trace,
        }

    def test_history_is_59_fields_and_uses_only_previous_command(self):
        baseline = self._baseline()
        sequence, padded = s13._history_sequence(baseline, self._payload(), issue=16)
        self.assertEqual(sequence.shape, (17, 59))
        self.assertEqual(padded.shape, (1020,))
        np.testing.assert_array_equal(sequence[0, 35:52], np.zeros(17))
        np.testing.assert_allclose(sequence[1, 35:49], np.zeros(14))
        np.testing.assert_allclose(sequence[2, 35:49], np.full(14, 0.01))
        self.assertEqual(sequence[0, 52], 0.0)
        self.assertEqual(sequence[1, 52], 1.0)

    def test_response_input_is_pre_action_nominal_not_post_effect_current(self):
        baseline = self._baseline(length=2)
        baseline["spec"].update({
            "r3c3_probe_issue_step": -1, "r3c3_probe_first_effect_state": -1,
        })
        baseline["controller_trace"][0]["r3c3t13s9_actuator_prediction"] = {
            "nominal_readback_current_a_tsc": [0.0] * 14,
            "readback_lower_a_tsc": [-0.1] * 14,
            "readback_upper_a_tsc": [0.1] * 14,
            "card15_fields": ["0.00000000"] * 14,
        }
        baseline["controller_trace"][0]["r3c3t13s9_center_card15_fields"] = ["0.00000000"] * 14
        probe = copy.deepcopy(baseline)
        probe["spec"].update({"r3c3_probe_issue_step": 0, "r3c3_probe_first_effect_state": 1})
        probe["controller_trace"][0]["r3c3t13s9_actuator_prediction"] = {
            "nominal_readback_current_a_tsc": [1.0] * 14,
            "readback_lower_a_tsc": [0.9] * 14,
            "readback_upper_a_tsc": [1.1] * 14,
            "card15_fields": ["0.00000000"] * 14,
        }
        probe["controller_trace"][0]["r3c3t13s9_center_card15_fields"] = ["0.00000000"] * 14
        probe["trajectory"][1]["currents_a_tsc"] = [2.05] * 14
        response = s13._response(probe, baseline, self._payload())
        np.testing.assert_allclose(response["u_center"], np.full(14, 0.01))
        self.assertFalse(np.array_equal(response["u_center"], response["actual_current"]))
        self.assertTrue(response["actuator_input_box_containment_pass"])
        self.assertFalse(response["post_effect_current_model_input_used"])

    def test_reservoir_is_deterministic(self):
        recurrent, inputs = s13._reservoir_weights(20260802, 32)
        sequence = np.arange(5 * 59, dtype=float).reshape(5, 59) / 1000.0
        one = s13._encode_sequence(sequence, recurrent, inputs, rho=0.65, leak=0.5, input_scale=0.25)
        two = s13._encode_sequence(sequence, recurrent, inputs, rho=0.65, leak=0.5, input_scale=0.25)
        np.testing.assert_array_equal(one, two)

    def test_model_prediction_is_zero_at_zero_action(self):
        model = {
            "hyper": {"rho": 0.65, "leak": 0.5, "observer_rank": 4, "ridge": 1e-6},
            "history_mean": [0.0] * 32,
            "history_basis": np.eye(32)[:4].tolist(),
            "history_rms": [1.0] * 4,
            "action_basis": np.eye(14)[:4].tolist(),
            "action_rms": [1.0] * 4,
            "coefficients": np.ones((20, 5)).tolist(),
        }
        row = {"sequence": np.zeros((1, 59)), "u_center": np.zeros(14)}
        predicted, derivative = s13._predict(row, model, self.cfg["observer"])
        np.testing.assert_array_equal(predicted, np.zeros(5))
        self.assertEqual(derivative.shape, (14, 5))

    def test_phase_order_fails_closed(self):
        ctx = SimpleNamespace(paths=SimpleNamespace(state=Path("state.json")))
        with mock.patch.object(s13, "_state", return_value={"phase_status": "offline_ready"}):
            s13._require_phase(ctx, "offline_ready")
            with self.assertRaises(ValueError):
                s13._require_phase(ctx, "calibration_tube_frozen")
        with mock.patch.object(s13, "_state", return_value={
            "phase_status": "training_probe_complete", "finished": True,
            "stop_reason": "training_probe_runtime_gate_failed",
        }):
            with self.assertRaisesRegex(ValueError, "fail-closed"):
                s13._require_phase(ctx, "training_probe_complete")

    def test_near_alias_across_source_pairs_fails_closed(self):
        row = {
            "pair_id": "pair_a", "padded_history": np.zeros(1020),
            "u_center": np.zeros(14),
        }
        other = copy.deepcopy(row)
        other["pair_id"] = "pair_b"
        other["u_center"][0] = 0.5e-12
        audit = s13._alias_audit([row, other], self.cfg["observer"])
        self.assertFalse(audit["passed"])
        self.assertEqual(audit["disjoint_near_nonexact_alias_pair_count"], 1)

    def test_launcher_treats_controller_bank_as_file(self):
        text = (ROOT / "run_stage4_2r3c3t13s13_common.sh").read_text(encoding="utf-8")
        self.assertIn(
            'for path in "${SOURCE_T3_BANK}" "${Q1_AUDIT}"', text,
        )
        directory_loop = text.split('for path in "${SOURCE_R3B}"', 1)[1].split("done", 1)[0]
        self.assertNotIn('"${SOURCE_T3_BANK}"', directory_loop)

    def test_snapshot_contract_uses_inventory_digest_not_manifest_file_hash(self):
        context = {
            "pair_id": "pair", "history_member": "plus_first",
            "state_generation_experiment_id": "state",
            "restart_snapshot_dir": str(ROOT / ".codex_tmp" / "snapshot_contract"),
            "restart_snapshot_manifest_digest": "inventory-digest",
        }
        manifest = {"digest": "inventory-digest"}
        with mock.patch.object(s13, "_read_json", return_value=manifest), mock.patch.object(
            s13.s9.t11.t1.r1, "_validate_snapshot_inventory", return_value=True,
        ), mock.patch.object(s13, "_sha256", side_effect=AssertionError("file SHA is not the snapshot identity")):
            audit = s13._validate_snapshots([context] * 72)
        self.assertTrue(audit["passed"])
        self.assertEqual(audit["pass_count"], 72)


if __name__ == "__main__":
    unittest.main()
