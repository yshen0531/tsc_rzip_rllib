import copy
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r32_independent_forensics as independent32,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r33_independent_forensics as independent33,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r31_aligned_explicit_four_coordinate_feedback_sentinel
    as r8r31,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r32_rank_regularized_schedule_generalizing_feedback_preflight
    as r8r32,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight
    as r8r33,
)


class R8R33UniformRank12PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t13s24d1r14r8r33_uniformly_supported_rank12_schedule_generalizing_feedback_preflight.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_config_is_valid_and_zero_tsc(self):
        r8r33.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(self.cfg["model_contract"]["pca_rank"], 12)
        self.assertEqual(self.cfg["model_contract"]["transformed_dimension"], 78)
        self.assertTrue(self.cfg["scientific_scope"]["zero_new_tsc"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_frozen_config_rejects_rank_search_or_cap_change(self):
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["pca_rank"] = 13
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r33.validate_config(changed, project_root=self.root)

        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["hyperparameter_search_allowed"] = True
        with self.assertRaisesRegex(ValueError, "frozen config changed"):
            r8r33.validate_config(changed, project_root=self.root)

    def test_source_contract_authenticates_final_r8r32_artifacts(self):
        source = self.cfg["source_r8r32"]
        self.assertEqual(
            source["required_route"],
            "RANK_REGULARIZED_SCHEDULE_GENERALIZATION_PREFLIGHT_FAIL_NO_TSC",
        )
        for key in (
            "primary_summary_sha256",
            "primary_detailed_sha256",
            "model_sha256",
            "independent_sha256",
            "compact_audit_sha256",
            "final_report_sha256",
            "stage_state_sha256",
            "stage_manifest_sha256",
        ):
            self.assertEqual(len(source[key]), 64)

    @staticmethod
    def _rows(count=180):
        random = np.random.RandomState(3301)
        rows = []
        for index in range(count):
            feature = random.normal(size=44)
            q = random.uniform(-1.0, 1.0, size=4)
            previous = random.uniform(-1.0, 1.0, size=4)
            rows.append(
                {
                    "feature": feature,
                    "q": q,
                    "previous_q": previous,
                    "expanded": r8r31.expanded_feature238(feature, q, previous),
                    "targets": np.asarray(
                        [random.normal(scale=0.1, size=5) + index * 1e-6]
                    ),
                }
            )
        return rows

    def test_rank12_transform_has_exact_fixed_dimensions(self):
        head = r8r32.fit_head(self._rows(), offset=0, cfg=self.cfg)
        self.assertEqual(head["base_loadings"].shape, (44, 12))
        self.assertEqual(head["transformed_mean"].shape, (78,))
        self.assertEqual(head["transformed_coefficients"].shape, (78, 5))
        self.assertEqual(head["coefficients"].shape, (238, 5))

    def test_normal_and_independent_augmented_predictions_agree(self):
        rows = self._rows()
        primary = r8r32.fit_head(rows, offset=0, cfg=self.cfg, solver="normal")
        audited = independent32._fit_head(
            rows, offset=0, cfg=self.cfg, solver="augmented_lstsq"
        )
        expanded = np.asarray([row["expanded"] for row in rows])
        left = primary["intercept"] + expanded @ primary["coefficients"]
        right = audited["intercept"] + expanded @ audited["coefficients"]
        self.assertLessEqual(float(np.max(np.abs(left - right))), 1e-12)

    def test_model_kind_records_actual_rank12(self):
        rows = self._rows(80)
        trajectories = [
            {
                "intervals": [dict(row) for _ in range(6)],
            }
            for row in rows
        ]
        model = r8r32.fit_model(trajectories, lambda _row: True, self.cfg)
        self.assertEqual(model["model_kind"], "rank_regularized_pca12_ridge_0p01")

    def test_summary_uses_r8r33_identity_and_blocks_learning(self):
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
                "passed": True,
                "head_count": 1161,
                "failed_head_count": 0,
                "minimum_numerical_rank": 13,
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
        summary = r8r33._summary(detailed, "model")
        self.assertEqual(summary["stage"], r8r33.STAGE)
        self.assertEqual(summary["identity"], r8r33.IDENTITY)
        self.assertFalse(summary["controller_execution_authorized"])
        self.assertFalse(summary["expert_data_allowed"])

    def test_independent_helpers_are_separate_from_primary_and_fail_closed(self):
        self.assertIsNot(independent32._fit_head, r8r32.fit_head)
        self.assertIs(independent33._maximum_difference, independent32._maximum_difference)
        self.assertTrue(
            np.isinf(
                independent33._maximum_difference(
                    {"rank": 12, "passed": True},
                    {"rank": 12, "passed": False},
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
