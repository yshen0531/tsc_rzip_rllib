from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import stage4_1r17_original_deadline_one_sided_robust_braking_closure as r17


class Stage41R17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.cfg = json.loads(
            (
                cls.root
                / "configs/stage4_1r17_original_deadline_one_sided_robust_braking_closure_370ms.json"
            ).read_text(encoding="utf-8")
        )

    def test_config_and_self_test(self) -> None:
        r17.validate_config(self.cfg)
        payload = r17.self_test(self.root)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["expected_true_tsc_oracle_rollouts"], 2)
        self.assertEqual(payload["expected_true_tsc_calibrated_rollouts"], 4)
        self.assertEqual(payload["maximum_true_tsc_rollouts"], 6)
        self.assertAlmostEqual(payload["maximum_schedule_component"], 0.105, places=12)
        self.assertFalse(payload["bidirectional_response_model_validated"])

    def test_delay_conditioned_schedules_are_zero_net(self) -> None:
        payload = r17.self_test(self.root)
        self.assertEqual(payload["delay_conditioned_schedules"]["d1"]["magnitude"], 6.0)
        self.assertEqual(payload["delay_conditioned_schedules"]["d2"]["magnitude"], 7.0)
        np.testing.assert_allclose(
            payload["delay_conditioned_schedules"]["d1"]["net"], np.zeros(3), atol=1e-12
        )
        np.testing.assert_allclose(
            payload["delay_conditioned_schedules"]["d2"]["net"], np.zeros(3), atol=1e-12
        )

    def test_validation_rejects_timing_drift(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["formal_timing_contract"]["weak_slew"]["arrival_deadline_step"] = 28
        with self.assertRaises(ValueError):
            r17.validate_config(cfg)

    def test_validation_rejects_posthoc_magnitude_change(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["one_sided_candidate"]["new_delay2_magnitude"] = 7.5
        with self.assertRaises(ValueError):
            r17.validate_config(cfg)

    def test_validation_rejects_bidirectional_claim(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        cfg["bidirectional_response_model_validated"] = True
        with self.assertRaises(ValueError):
            r17.validate_config(cfg)

    def test_source_inventory_includes_all_32_raw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for path in r17._required_source_files(source):
                if "raw" not in path.parts:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            raw_dir = source / "stage4_1r16_amplitude_envelope_validation" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            for index in range(32):
                (raw_dir / f"source_{index:02d}.json.gz").write_bytes(b"x")
            inventory = r17._source_inventory(source)
            self.assertEqual(inventory["inventory_contract"], r17.SOURCE_INVENTORY_CONTRACT)
            self.assertEqual(inventory["n_files"], 45)
            self.assertEqual(
                sum("/raw/" in row["relative_path"] for row in inventory["files"]), 32
            )

    def test_source_inventory_changes_when_raw_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            for path in r17._required_source_files(source):
                if "raw" not in path.parts:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("{}", encoding="utf-8")
            raw_dir = source / "stage4_1r16_amplitude_envelope_validation" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            for index in range(32):
                (raw_dir / f"source_{index:02d}.json.gz").write_bytes(b"x")
            before = r17._source_inventory(source)["digest"]
            (raw_dir / "source_00.json.gz").write_bytes(b"changed")
            after = r17._source_inventory(source)["digest"]
            self.assertNotEqual(before, after)

    def test_exact_probe_application_is_stepwise_not_max_only(self) -> None:
        result = {
            "spec": {"r15_probe_delta_by_issue_step": {"2": [0.1, 0.0, 0.0], "3": [-0.1, 0.0, 0.0]}},
            "anticipatory_damping_trace": [
                {
                    "step": 2,
                    "r15_identification_probe": True,
                    "r15_probe_requested_delta": [0.1, 0.0, 0.0],
                    "r15_probe_applied_delta": [0.1, 0.0, 0.0],
                },
                {
                    "step": 3,
                    "r15_identification_probe": True,
                    "r15_probe_requested_delta": [-0.1, 0.0, 0.0],
                    "r15_probe_applied_delta": [-0.1, 0.0, 0.0],
                },
            ],
        }
        self.assertTrue(r17._exact_probe_application(result))
        result["anticipatory_damping_trace"][1]["r15_probe_applied_delta"] = [0.1, 0.0, 0.0]
        self.assertFalse(r17._exact_probe_application(result))

    def test_oracle_specs_only_run_delay2_at_fixed_7x(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg, r16_ctx=SimpleNamespace())
        def fake_base(_ctx, **kwargs):
            return {
                "target_id": kwargs["target"]["target_id"],
                "action_delay_steps": kwargs["actual_delay"],
                "modeled_delay_steps": kwargs["modeled_delay"],
                "r16_magnitude": kwargs["magnitude"],
                "r16_direction_sign": kwargs["direction_sign"],
                "environment_variant": kwargs["environment_variant"],
            }
        with mock.patch.object(r17, "materialize_variant", return_value=("v", {})), mock.patch.object(
            r17.r16, "_base_spec", side_effect=fake_base
        ):
            specs = r17._oracle_specs(ctx)
        self.assertEqual(len(specs), 2)
        self.assertEqual({spec["action_delay_steps"] for spec in specs}, {2})
        self.assertEqual({spec["r17_delay_conditioned_magnitude"] for spec in specs}, {7.0})
        self.assertEqual({spec["r16_direction_sign"] for spec in specs}, {-1})

    def test_calibrated_specs_use_6x_for_delay1_and_7x_for_delay2(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        tokens = {
            (1, 0.9): {
                "experiment_id": "token1",
                "batch_trusted_correct": True,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 1,
            },
            (2, 0.9): {
                "experiment_id": "token2",
                "batch_trusted_correct": True,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 2,
            },
        }
        with mock.patch.object(r17, "_trusted_tokens", return_value=tokens), mock.patch.object(
            r17, "_make_spec", side_effect=lambda _ctx, **kwargs: dict(kwargs)
        ):
            specs = r17._calibrated_specs(ctx)
        self.assertEqual(len(specs), 4)
        mapping = {(spec["actual_delay"], spec["magnitude"]) for spec in specs}
        self.assertEqual(mapping, {(1, 6.0), (2, 7.0)})

    def test_calibrated_specs_reject_untrusted_token(self) -> None:
        ctx = SimpleNamespace(cfg=self.cfg)
        tokens = {
            (1, 0.9): {
                "experiment_id": "bad",
                "batch_trusted_correct": False,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 1,
            },
            (2, 0.9): {
                "experiment_id": "good",
                "batch_trusted_correct": True,
                "batch_wrong_accept": False,
                "batch_selected_delay_steps": 2,
            },
        }
        with mock.patch.object(r17, "_trusted_tokens", return_value=tokens):
            with self.assertRaises(ValueError):
                r17._calibrated_specs(ctx)


    def test_model_output_vector_uses_r15_inclusive_contract(self) -> None:
        sentinel = np.arange(75, dtype=float)
        with mock.patch.object(r17.r15, "_output_vector", return_value=sentinel) as fn:
            actual = r17._model_output_vector({"trajectory": []})
        np.testing.assert_array_equal(actual, sentinel)
        fn.assert_called_once_with(
            {"trajectory": []}, start_state=23, end_state_inclusive=37
        )
        self.assertFalse(hasattr(r17.r16.r15b, "_output_vector"))

    def test_model_output_vector_rejects_wrong_shape(self) -> None:
        with mock.patch.object(r17.r15, "_output_vector", return_value=np.zeros(74)):
            with self.assertRaisesRegex(ValueError, "shape mismatch"):
                r17._model_output_vector({"trajectory": []})

    def test_legacy_r17_manifest_upgrades_without_changing_scientific_identity(self) -> None:
        current = {
            "controller_revision": r17.CONTROLLER_REVISION,
            "package_revision": r17.PACKAGE_REVISION,
            "source_stage4_1r16_run": "/source/r16",
            "source_fingerprint": {"digest": "abc"},
            "formal_timing_contract": self.cfg["formal_timing_contract"],
            "delay_conditioned_magnitudes": {"delay1": 6.0, "delay2": 7.0},
            "candidate_fixed_before_new_tsc": True,
        }
        old = {
            **copy.deepcopy(current),
            "package_revision": "r17_delay_conditioned_one_sided_margin_closure_v1",
            "created_utc": "before",
        }
        upgraded = r17._validated_resume_manifest(old, current)
        self.assertEqual(upgraded["package_revision"], r17.PACKAGE_REVISION)
        self.assertIn(
            "r17_delay_conditioned_one_sided_margin_closure_v1",
            upgraded["package_revision_history"],
        )
        self.assertTrue(upgraded["output_vector_contract_hotfix"])
        self.assertEqual(upgraded["source_fingerprint"], {"digest": "abc"})

    def test_unknown_resume_package_revision_is_rejected(self) -> None:
        current = {
            "controller_revision": r17.CONTROLLER_REVISION,
            "package_revision": r17.PACKAGE_REVISION,
            "source_stage4_1r16_run": "/source/r16",
            "source_fingerprint": {"digest": "abc"},
            "formal_timing_contract": self.cfg["formal_timing_contract"],
            "delay_conditioned_magnitudes": {"delay1": 6.0, "delay2": 7.0},
            "candidate_fixed_before_new_tsc": True,
        }
        old = {**copy.deepcopy(current), "package_revision": "unknown"}
        with self.assertRaisesRegex(ValueError, "not an approved R17/R17a"):
            r17._validated_resume_manifest(old, current)

    def test_finite_scope_and_no_rl_claims(self) -> None:
        self.assertTrue(self.cfg["finite_test_envelope_only"])
        self.assertFalse(self.cfg["bidirectional_response_model_validated"])
        self.assertFalse(self.cfg["unseen_target_generalization_validated"])
        self.assertTrue(self.cfg["stage4_2r1_was_not_run_or_reused"])
        self.assertIn("BC", self.cfg["next_if_pass"])
        self.assertIn("7.5x", self.cfg["next_if_fail"])


if __name__ == "__main__":
    unittest.main()
