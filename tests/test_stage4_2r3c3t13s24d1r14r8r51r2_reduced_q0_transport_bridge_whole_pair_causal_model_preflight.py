from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r2_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r2_reduced_q0_transport_bridge_whole_pair_causal_model_preflight as r51r2,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / (
    "stage4_2r3c3t13s24d1r14r8r51r2_"
    "reduced_q0_transport_bridge_whole_pair_causal_model_preflight.json"
)


class R8R51R2WholePairCausalModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    @staticmethod
    def _trajectory() -> list[dict[str, object]]:
        rows = []
        for step in range(15):
            rows.append(
                {
                    "R": 1.5 + 0.01 * step,
                    "Z": -0.2 + 0.02 * step,
                    "Ip": 100000.0 + 100.0 * step,
                    "currents_a_tsc": (np.arange(14, dtype=float) + step).tolist(),
                }
            )
        return rows

    def test_frozen_config_and_design_hash(self) -> None:
        r51r2.validate_config(self.cfg, ROOT)
        independent.validate_config(self.cfg, ROOT)
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(
            hashlib.sha256(design.read_bytes()).hexdigest(),
            self.cfg["design_document_sha256"],
        )
        self.assertEqual(self.cfg["model_contract"]["row_count"], 208)
        self.assertTrue(self.cfg["scientific_scope"]["zero_new_tsc"])
        self.assertFalse(
            self.cfg["scientific_scope"][
                "all_source_trajectories_allowed_in_expert_dataset"
            ]
        )

    def test_contract_mutations_fail_closed(self) -> None:
        for section, key, value in (
            ("feature_contract", "previous_current_state_step", 11),
            ("model_contract", "ridge_penalty", 0.001),
            ("model_contract", "tube_reserve_multiplier", 1.0),
            ("scientific_scope", "model_selection_allowed", True),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design changed"):
                r51r2.validate_config(changed, ROOT)

    def test_causal_feature_is_exact_44d_allowed_prefix(self) -> None:
        trajectory = self._trajectory()
        scales = np.arange(1.0, 15.0)
        feature = r51r2.causal_feature44(trajectory, scales)
        self.assertEqual(feature.shape, (44,))
        expected_visible = np.asarray(
            [
                trajectory[step][name]
                for step in (9, 10, 11, 12)
                for name in ("R", "Z", "Ip")
            ],
            dtype=float,
        )
        self.assertTrue(np.array_equal(feature[:12], expected_visible))
        self.assertTrue(
            np.array_equal(
                feature[12:26],
                np.asarray(trajectory[12]["currents_a_tsc"]) / scales,
            )
        )
        self.assertTrue(np.array_equal(feature[-4:], np.zeros(4)))

    def test_primary_and_independent_expansion_agree_without_intercept(self) -> None:
        feature = np.linspace(-2.0, 2.0, 44)
        q = np.asarray([1.0, -0.5, 0.25, 1.5])
        mean = np.linspace(-0.5, 0.5, 44)
        scale = np.linspace(0.5, 2.5, 44)
        primary = r51r2.expanded_feature180(feature, q, mean, scale)
        audit = independent.expand(feature, q, mean, scale)
        self.assertEqual(primary.shape, (180,))
        self.assertTrue(np.array_equal(primary, audit))
        self.assertTrue(
            np.array_equal(
                r51r2.expanded_feature180(feature, np.zeros(4), mean, scale),
                np.zeros(180),
            )
        )

    def test_ridge_fit_dimensions_and_zero_q_prediction(self) -> None:
        generator = np.random.default_rng(20260810)
        rows = []
        pairs = [f"pair_{index}" for index in range(8)]
        for pair in pairs:
            for index in range(26):
                q = generator.normal(size=4)
                if index == 0:
                    q = np.zeros(4)
                rows.append(
                    {
                        "pair_id": pair,
                        "feature": generator.normal(size=44),
                        "q": q,
                        "normalized_response": generator.normal(size=6),
                    }
                )
        model = r51r2.fit_model(rows, pairs[:7], 1e-4)
        self.assertEqual(model["coefficients"].shape, (180, 6))
        prediction = r51r2.predict_model(model, [rows[0]])
        self.assertTrue(np.array_equal(prediction, np.zeros((1, 6))))

    def test_frozen_whole_pair_partition_counts(self) -> None:
        pairs = [f"pair_{index}" for index in range(8)]
        identities = [(pair, history, candidate) for pair in pairs for history in range(2) for candidate in range(13)]
        for held in pairs:
            self.assertEqual(sum(pair == held for pair, _, _ in identities), 26)
            training = [row for row in identities if row[0] != held]
            self.assertEqual(len(training), 182)
            for nested_held in [pair for pair in pairs if pair != held]:
                self.assertEqual(
                    sum(pair != nested_held for pair, _, _ in training), 156
                )

    def test_independent_comparison_separates_numeric_and_discrete(self) -> None:
        discrete, difference, reason = independent.compare(
            {"a": [1.0, True, "x"]}, {"a": [1.0 + 5e-13, True, "x"]}
        )
        self.assertTrue(discrete)
        self.assertLessEqual(difference, 1e-12)
        self.assertEqual(reason, "")
        discrete, difference, reason = independent.compare({"a": 1}, {"a": 2})
        self.assertFalse(discrete)
        self.assertEqual(difference, 0.0)
        self.assertIn("values differ", reason)

    def test_independent_implementation_does_not_import_primary(self) -> None:
        source = inspect.getsource(independent)
        self.assertNotIn("import stage4_2r3c3t13s24d1r14r8r51r2", source)
        self.assertNotIn("from tsc_rzip_rllib.diagnostics", source)


if __name__ == "__main__":
    unittest.main()
