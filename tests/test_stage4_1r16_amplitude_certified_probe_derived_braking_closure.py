from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r16_amplitude_certified_probe_derived_braking_closure as r16


class Stage41R16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (
                cls.root
                / "configs/stage4_1r16_amplitude_certified_probe_derived_braking_closure_370ms.json"
            ).read_text(encoding="utf-8")
        )
        cls.r15_cfg = json.loads(
            (
                cls.root
                / "configs/stage4_1r15_bounded_early_braking_local_response_identification_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def _schedule_ctx(self) -> SimpleNamespace:
        return SimpleNamespace(r15b_ctx=SimpleNamespace(source_cfg=self.r15_cfg))

    def test_config_and_self_test(self) -> None:
        r16.validate_config(self.cfg)
        payload = r16.self_test(self.root)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["expected_true_tsc_amplitude_rollouts"], 32)
        self.assertEqual(payload["expected_true_tsc_calibrated_rollouts"], 4)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 36)
        self.assertTrue(payload["formal_timing_contract_immutable"])

    def test_amplitude_ladder_schedules_are_zero_net_and_bounded(self) -> None:
        ctx = self._schedule_ctx()
        maximum = 0.0
        variants = 0
        for delay in (1, 2):
            for magnitude in (1.0, 2.0, 4.0, 6.0):
                for sign in (-1, 1):
                    coefficients = sign * magnitude * np.ones(4, dtype=float)
                    schedule = r16._combined_schedule(
                        ctx, actual_delay=delay, coefficients=coefficients
                    )
                    self.assertGreater(len(schedule), 0)
                    net = np.sum(np.stack(list(schedule.values())), axis=0)
                    np.testing.assert_allclose(net, np.zeros(3), atol=1e-12, rtol=0.0)
                    local_max = max(float(np.max(np.abs(v))) for v in schedule.values())
                    self.assertAlmostEqual(local_max, 0.015 * magnitude, places=12)
                    maximum = max(maximum, local_max)
                    variants += 1
        self.assertEqual(variants, 16)
        self.assertAlmostEqual(maximum, 0.09, places=12)

    def test_predicted_result_updates_only_modelled_state_fields(self) -> None:
        trajectory = [
            {
                "R": 1.0 + 0.001 * index,
                "Z": -0.5 + 0.001 * index,
                "Ip": 1000.0 + index,
                "currents_a_display": [0.0] * 14,
            }
            for index in range(38)
        ]
        baseline = {"trajectory": trajectory, "success": False, "failure_reason": "x"}
        baseline_output = np.zeros(75)
        basis = np.zeros((4, 75))
        basis[0, 30:45] = np.arange(15) + 2.0
        basis[1, 45:60] = -(np.arange(15) + 3.0)
        basis[2, 60:75] = np.arange(15) + 4.0
        model = {
            "baseline_output": baseline_output.tolist(),
            "basis_odd_response": basis.tolist(),
        }
        original = copy.deepcopy(baseline)
        result = r16._predicted_result_from_model(baseline, model, [1.0, 1.0, 1.0, 0.0])
        self.assertEqual(baseline, original)
        self.assertTrue(result["success"])
        self.assertEqual(result["failure_reason"], "")
        for local, state in enumerate(range(23, 38)):
            self.assertAlmostEqual(result["trajectory"][state]["R"], local + 2.0)
            self.assertAlmostEqual(result["trajectory"][state]["Z"], -(local + 3.0))
            self.assertAlmostEqual(result["trajectory"][state]["Ip"], local + 4.0)
        self.assertEqual(result["trajectory"][22], baseline["trajectory"][22])

    def test_source_inventory_includes_every_superposition_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for path in r16._required_source_files(source):
                if "raw" not in path.parts:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            raw_dir = source / "stage4_1r15b_superposition_validation" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            for index in range(32):
                (raw_dir / f"probe_{index:02d}.json.gz").write_bytes(b"x")
            inventory = r16._source_inventory(source)
            self.assertEqual(inventory["inventory_contract"], r16.SOURCE_INVENTORY_CONTRACT)
            self.assertEqual(inventory["n_files"], 46)
            self.assertEqual(
                sum("/raw/" in row["relative_path"] for row in inventory["files"]),
                32,
            )

    def test_source_inventory_changes_when_raw_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            nonraw = [p for p in r16._required_source_files(source) if "raw" not in p.parts]
            for path in nonraw:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")
            raw_dir = source / "stage4_1r15b_superposition_validation" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            for index in range(32):
                (raw_dir / f"probe_{index:02d}.json.gz").write_bytes(b"x")
            before = r16._source_inventory(source)["digest"]
            (raw_dir / "probe_00.json.gz").write_bytes(b"changed")
            after = r16._source_inventory(source)["digest"]
            self.assertNotEqual(before, after)

    def test_validation_rejects_relaxed_timing(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaises(ValueError):
            r16.validate_config(cfg)

    def test_validation_rejects_changed_amplitude_ladder(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["amplitude_envelope_validation"]["magnitude_levels"] = [1.0, 2.0, 4.0, 5.0]
        with self.assertRaises(ValueError):
            r16.validate_config(cfg)

    def test_validation_rejects_posthoc_candidate_change(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["amplitude_envelope_validation"]["closure_candidate_magnitude"] = 4.0
        with self.assertRaises(ValueError):
            r16.validate_config(cfg)

    def test_calibrated_specs_reject_untrusted_token(self) -> None:
        ctx = SimpleNamespace(
            cfg=self.cfg,
            r15b_ctx=SimpleNamespace(),
        )
        token = {
            "experiment_id": "bad",
            "batch_trusted_correct": False,
            "batch_wrong_accept": False,
            "batch_selected_delay_steps": 1,
        }
        with mock.patch.object(r16, "_trusted_tokens", return_value={(1, 0.9): token, (2, 0.9): token}), mock.patch.object(
            r16, "materialize_variant", return_value=("variant", {})
        ):
            with self.assertRaises(ValueError):
                r16._calibrated_specs(ctx)

    def test_formal_policy_keeps_original_deadline(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        policy = r16._formal_policy(ctx, policy_id="test")
        self.assertEqual(policy["horizon_steps"], 37)
        self.assertEqual(max(policy["allowed_arrival_steps"]), 27)

    def test_fixed_candidate_requires_all_four_and_positive_margin(self) -> None:
        amp = self.cfg["amplitude_envelope_validation"]
        self.assertTrue(amp["require_candidate_all_four_formal_pass"])
        self.assertEqual(amp["closure_candidate_magnitude"], 6.0)
        self.assertGreaterEqual(amp["minimum_candidate_formal_signed_margin"], 0.01)
        self.assertEqual(amp["braking_sign"], -1)

    def test_stage_does_not_claim_generalization_or_restart(self) -> None:
        self.assertTrue(self.cfg["finite_test_envelope_only"])
        self.assertFalse(self.cfg["unseen_target_generalization_validated"])
        self.assertTrue(self.cfg["stage4_2r1_was_not_run_or_reused"])
        self.assertIn("BC/DAgger/RL", self.cfg["next_if_pass"])


if __name__ == "__main__":
    unittest.main()
