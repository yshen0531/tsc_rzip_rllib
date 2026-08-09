import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r32_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
    as r8r32,
)


class R8R32RankRegularizedPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_config_is_valid_and_zero_tsc(self):
        r8r32.validate_config(self.cfg, project_root=self.root)
        self.assertTrue(self.cfg["scientific_scope"]["zero_new_tsc"])
        self.assertFalse(self.cfg["scientific_scope"]["controller_execution_authorized"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_frozen_config_rejects_transform_or_gate_change(self):
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["pca_rank"] = 31
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r32.validate_config(changed, project_root=self.root)

        changed = copy.deepcopy(self.cfg)
        changed["model_gates"]["maximum_tube_half_width"][4] = 0.081
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r32.validate_config(changed, project_root=self.root)

    def test_expanded_to_transformed_affine_map_is_exact(self):
        random = np.random.RandomState(3201)
        mean = random.normal(size=44)
        scale = np.exp(random.normal(size=44))
        loadings, _ = np.linalg.qr(random.normal(size=(44, 32)))
        matrix, constant = r8r32._expanded_to_transformed_map(mean, scale, loadings)
        feature = random.normal(size=44)
        q = random.normal(size=4)
        previous_q = random.normal(size=4)
        expanded = r8r31.expanded_feature238(feature, q, previous_q)
        score = ((feature - mean) / scale) @ loadings
        expected = np.concatenate(
            (score, expanded[44:62], *(score * value for value in q))
        )

        self.assertEqual(matrix.shape, (238, 178))
        np.testing.assert_allclose(constant + expanded @ matrix, expected, atol=2e-14)

    def test_pca_sign_is_canonical_and_rank_deficiency_fails_closed(self):
        random = np.random.RandomState(3202)
        value = random.normal(size=(96, 44))
        loadings, singular = r8r32._canonical_loadings(value, self.cfg)
        self.assertEqual(loadings.shape, (44, 32))
        self.assertEqual(singular.shape, (44,))
        for column in range(32):
            pivot = int(np.argmax(np.abs(loadings[:, column])))
            self.assertGreaterEqual(loadings[pivot, column], 0.0)

        with self.assertRaisesRegex(ValueError, "rank below 32"):
            r8r32._canonical_loadings(np.ones((96, 44)), self.cfg)

    @staticmethod
    def _synthetic_rows(count=420):
        random = np.random.RandomState(3203)
        output = []
        response_weights = random.normal(scale=0.01, size=(178, 5))
        for index in range(count):
            feature = random.normal(size=44)
            q = random.uniform(-1.0, 1.0, size=4)
            previous_q = random.uniform(-1.0, 1.0, size=4)
            expanded = r8r31.expanded_feature238(feature, q, previous_q)
            # The target need only be finite for the normal/augmented solver audit.
            target = random.normal(scale=0.1, size=5) + index * 1e-6
            output.append(
                {
                    "feature": feature,
                    "q": q,
                    "previous_q": previous_q,
                    "expanded": expanded,
                    "targets": np.asarray([target]),
                    "unused_weights": response_weights,
                }
            )
        return output

    def test_normal_and_augmented_solves_agree_on_predictions(self):
        rows = self._synthetic_rows()
        primary = r8r32.fit_head(rows, offset=0, cfg=self.cfg, solver="normal")
        audited = independent._fit_head(
            rows, offset=0, cfg=self.cfg, solver="augmented_lstsq"
        )
        expanded = np.asarray([row["expanded"] for row in rows])
        primary_prediction = primary["intercept"] + expanded @ primary["coefficients"]
        audited_prediction = audited["intercept"] + expanded @ audited["coefficients"]

        self.assertLessEqual(
            float(np.max(np.abs(primary_prediction - audited_prediction))), 1e-12
        )

    def test_fit_head_uses_training_only_transform_and_fixed_dimensions(self):
        rows = self._synthetic_rows()
        head = r8r32.fit_head(rows, offset=0, cfg=self.cfg)
        self.assertEqual(head["base_mean"].shape, (44,))
        self.assertEqual(head["base_loadings"].shape, (44, 32))
        self.assertEqual(head["transformed_mean"].shape, (178,))
        self.assertEqual(head["transformed_coefficients"].shape, (178, 5))
        self.assertEqual(head["coefficients"].shape, (238, 5))
        np.testing.assert_allclose(
            head["base_mean"], np.mean([row["feature"] for row in rows], axis=0)
        )

    def test_bank_contract_rejects_any_digest_or_count_change(self):
        evidence = {
            "trajectory_count": 560,
            "context_count": 16,
            "schedule_count": 35,
            "interval_record_count": 3360,
            "bank_digest": self.cfg["bank_contract"]["bank_digest"],
            "feature_digest": self.cfg["bank_contract"]["feature_digest"],
            "target_digest": self.cfg["bank_contract"]["target_digest"],
        }
        r8r32._verify_bank(evidence, self.cfg)
        changed = dict(evidence)
        changed["target_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "bank reproduction changed"):
            r8r32._verify_bank(changed, self.cfg)

    def test_rank_audit_runs_both_fold_families_and_fails_closed(self):
        trajectories = []
        for pair in ("p0", "p1"):
            for schedule in ("s0", "s1"):
                row = {
                    "feature": np.ones(44),
                    "q": np.zeros(4),
                    "expanded": np.zeros(238),
                    "targets": np.zeros((1, 5)),
                }
                trajectories.append(
                    {
                        "pair_id": pair,
                        "schedule_id": schedule,
                        "intervals": [dict(row) for _ in range(6)],
                    }
                )
        audit = r8r32.representation_rank_audit(trajectories, self.cfg)

        self.assertFalse(audit["passed"])
        self.assertEqual(audit["family_count"], 2)
        self.assertEqual(audit["head_count"], 24)
        self.assertEqual(audit["failed_head_count"], 24)
        self.assertEqual(audit["minimum_numerical_rank"], 0)

    def test_independent_projection_ignores_only_non_load_bearing_digests(self):
        left = {"solver": "normal", "model_digest": "a", "value": [1.0, True]}
        right = {
            "solver": "augmented_lstsq",
            "model_digest": "b",
            "value": [1.0 + 5e-13, True],
        }
        difference = independent._maximum_difference(
            independent._without_digests(left), independent._without_digests(right)
        )
        self.assertAlmostEqual(difference, 5e-13, places=16)
        right["value"][1] = False
        self.assertTrue(
            np.isinf(
                independent._maximum_difference(
                    independent._without_digests(left),
                    independent._without_digests(right),
                )
            )
        )

    def test_phase_closed_summary_does_not_authorize_execution_or_learning(self):
        detailed = {
            "bank_evidence": {
                "trajectory_count": 560,
                "schedule_count": 35,
                "interval_record_count": 3360,
                "bank_digest": "bank",
                "feature_digest": "feature",
                "target_digest": "target",
            },
            "representation_rank_audit": {
                "passed": False,
                "head_count": 989,
                "failed_head_count": 1,
                "minimum_numerical_rank": 31,
            },
            "outer_model_evaluation": {
                "passed": True,
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
        summary = r8r32._summary(detailed, "model")
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["gate_a_qualified"])
        self.assertFalse(summary["expert_data_allowed"])
        self.assertFalse(summary["real_tsc_executed"])
        self.assertEqual(summary["plant_step_count"], 0)


if __name__ == "__main__":
    unittest.main()
