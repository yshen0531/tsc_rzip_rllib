import copy
import inspect
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r34_independent_forensics as independent34,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight
    as r8r34,
)


class R8R34CausalLocalNeighborhoodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r34_causal_local_neighborhood_schedule_generalizing_feedback_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    @staticmethod
    def _trajectories(count=80):
        random = np.random.RandomState(3401)
        output = []
        for index in range(count):
            intervals = []
            previous = random.uniform(-1.0, 1.0, size=4)
            q = random.uniform(-1.0, 1.0, size=4)
            for interval, target_count in enumerate((2, 2, 2, 2, 4, 15)):
                feature = random.normal(size=44)
                expanded = r8r31.expanded_feature238(feature, q, previous)
                coordinate = np.concatenate((feature, expanded[44:62]))
                base = coordinate[:5] * np.asarray([0.1, -0.05, 0.02, 0.03, -0.04])
                targets = np.asarray(
                    [base + 0.001 * offset + index * 1e-7 for offset in range(target_count)]
                )
                intervals.append(
                    {
                        "interval": interval,
                        "feature": feature,
                        "q": q,
                        "previous_q": previous,
                        "expanded": expanded,
                        "targets": targets,
                    }
                )
                previous = q
                q = random.uniform(-1.0, 1.0, size=4)
            output.append(
                {
                    "trajectory_id": f"trajectory_{index:03d}",
                    "pair_id": f"pair_{index % 8}",
                    "schedule_id": f"schedule_{index % 35}",
                    "intervals": intervals,
                }
            )
        return output

    def test_frozen_config_validates_and_blocks_search(self):
        r8r34.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(self.cfg["model_contract"]["neighbor_count"], 64)
        self.assertEqual(self.cfg["model_contract"]["coordinate_dimension"], 62)
        self.assertEqual(
            self.cfg["model_contract"]["primary_independent_scaled_tolerance"],
            1e-9,
        )
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["neighbor_count"] = 63
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r34.validate_config(changed, project_root=self.root)

    def test_source_contract_binds_final_r8r33_failure(self):
        source = self.cfg["source_r8r33"]
        self.assertEqual(
            source["required_final_route"],
            "UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_EXECUTION_FAIL_STOP",
        )
        self.assertEqual(
            source["required_primary_route"],
            "UNIFORMLY_SUPPORTED_RANK12_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC",
        )
        for key, value in source.items():
            if key.endswith("_sha256"):
                self.assertEqual(len(value), 64)

    def test_coordinate_is_exact_causal_44_plus_action18(self):
        row = self._trajectories(1)[0]["intervals"][0]
        coordinate = r8r34.coordinate62(row)
        self.assertEqual(coordinate.shape, (62,))
        np.testing.assert_array_equal(coordinate[:44], row["feature"])
        np.testing.assert_array_equal(coordinate[44:], row["expanded"][44:62])

    def test_local_model_has_fixed_k64_and_expected_groups(self):
        model = r8r34.fit_model(self._trajectories(), lambda _row: True, self.cfg)
        self.assertEqual(model["model_kind"], "causal_local_affine_k64_ridge1")
        self.assertEqual(len(model["intervals"]), 6)
        self.assertEqual(model["intervals"][0]["groups"][0]["training_row_count"], 80)
        self.assertEqual(model["intervals"][0]["groups"][0]["sample_offsets"], [0, 1])
        self.assertEqual(model["intervals"][5]["groups"][0]["sample_offsets"], list(range(15)))

    def test_primary_and_independent_local_predictions_meet_scaled_gate(self):
        trajectories = self._trajectories()
        primary_model = r8r34.fit_model(trajectories, lambda _row: True, self.cfg)
        independent_model = independent34._fit_model(
            trajectories, lambda _row: True, self.cfg
        )
        row = trajectories[0]["intervals"][5]
        left = r8r34.predict(
            primary_model, row, self.cfg, solver="augmented_lstsq"
        )
        right = r8r34.predict(
            independent_model,
            row,
            self.cfg,
            solver="normal",
            predict_group_fn=independent34._predict_group,
        )
        physical = np.abs(left - right) * r8r34.FACTORS
        scales = np.asarray(
            self.cfg["model_contract"]["primary_independent_component_scales"]
        )
        self.assertLessEqual(float(np.max(physical / scales)), 1e-9)

    def test_neighbor_ties_are_deterministic(self):
        trajectories = self._trajectories(64)
        for trajectory in trajectories:
            row = trajectory["intervals"][0]
            row["feature"] = np.zeros(44)
            row["q"] = np.zeros(4)
            row["previous_q"] = np.zeros(4)
            row["expanded"] = r8r31.expanded_feature238(
                row["feature"], row["q"], row["previous_q"]
            )
        model = r8r34.fit_model(trajectories, lambda _row: True, self.cfg)
        row = trajectories[0]["intervals"][0]
        first = r8r34.predict(model, row, self.cfg, solver="augmented_lstsq")
        second = r8r34.predict(model, row, self.cfg, solver="augmented_lstsq")
        np.testing.assert_array_equal(first, second)

    def test_cardinality_audit_fails_closed_below_64(self):
        audit = r8r34.local_cardinality_audit(self._trajectories(70), self.cfg)
        self.assertFalse(audit["passed"])
        self.assertGreater(audit["failed_head_count"], 0)

    def test_plan_context_accepts_injected_predictor_without_changing_default(self):
        signature = inspect.signature(r8r31.plan_context)
        self.assertIn("predict_fn", signature.parameters)
        self.assertIs(signature.parameters["predict_fn"].default, r8r31.predict)

    def test_summary_blocks_learning_and_records_local_cardinality(self):
        detailed = {
            "bank_evidence": {
                "trajectory_count": 560,
                "schedule_count": 35,
                "interval_record_count": 3360,
                "bank_digest": "bank",
                "feature_digest": "feature",
                "target_digest": "target",
            },
            "local_cardinality_audit": {
                "passed": True,
                "head_count": 1161,
                "failed_head_count": 0,
                "minimum_training_row_count": 210,
            },
            "outer_model_evaluation": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
            },
            "schedule_jackknife": {
                "passed": False,
                "maximum_absolute_physical_error": [0.0] * 5,
                "maximum_reserved_physical_tube_half_width": [0.0] * 5,
            },
            "combined_tube_cap_passed": False,
            "model_gate_passed": False,
            "planning_evaluation": {
                "ran": False,
                "predicted_repaired_failed_baseline_count": 0,
                "predicted_fallback_plus_plan_oracle_count": 0,
                "nonzero_first_action_count": 0,
            },
            "scientific_gate_passed": False,
            "route": self.cfg["routes"]["model_fail"],
        }
        summary = r8r34._summary(detailed, "model")
        self.assertEqual(summary["local_cardinality_head_count"], 1161)
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["expert_data_allowed"])


if __name__ == "__main__":
    unittest.main()
