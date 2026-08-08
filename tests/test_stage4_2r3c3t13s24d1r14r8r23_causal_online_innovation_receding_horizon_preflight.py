from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r23_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight
    as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight.json"


def _synthetic_bank() -> list[dict]:
    rng = np.random.default_rng(20260809)
    output = []
    for pair_index in range(8):
        pair = f"pair_{pair_index}"
        for trajectory_index in range(4):
            intervals = []
            previous_q = np.zeros(2)
            for interval, count in enumerate((4, 4, 4, 5)):
                feature = rng.normal(size=42) + pair_index * 0.01
                q = np.asarray(
                    [0.25 * (trajectory_index % 2), 0.25 * ((trajectory_index + interval) % 2)],
                    dtype=float,
                )
                row = {
                    "row_id": f"{pair}|t{trajectory_index}|i{interval}",
                    "interval": interval,
                    "feature": feature,
                    "q": q,
                    "previous_q": previous_q.copy(),
                }
                row["expanded"] = primary._expanded_row(row)
                base = np.asarray(
                    [
                        0.01 * row["expanded"][0],
                        -0.02 * row["expanded"][1],
                        0.03 * row["expanded"][2],
                        0.04 * row["expanded"][3],
                        -0.05 * row["expanded"][4],
                    ]
                )
                row["targets"] = np.asarray(
                    [base + offset * np.asarray([1, 2, 3, 4, 5]) * 1e-4 for offset in range(count)]
                )
                intervals.append(row)
                previous_q = q
            output.append(
                {
                    "trajectory_id": f"{pair}|t{trajectory_index}",
                    "pair_id": pair,
                    "history_member": f"h{trajectory_index % 2}",
                    "schedule_id": f"s{trajectory_index}",
                    "intervals": intervals,
                }
            )
    return output


class R8R23ContractTests(unittest.TestCase):
    def test_config_and_frozen_contract(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        primary.validate_config(cfg, project_root=ROOT)
        self.assertEqual(cfg["bank_contract"]["trajectory_count_per_context"], 27)
        self.assertEqual(cfg["bank_contract"]["expanded_feature_dimension"], 133)
        self.assertEqual(cfg["action_contract"]["maximum_unfiltered_sequence_count"], 14641)
        self.assertEqual(cfg["model_contract"]["ridge_penalty"], 1e-4)
        self.assertEqual(cfg["model_contract"]["tube_reserve_multiplier"], 1.25)
        self.assertFalse(cfg["expert_data_allowed"])
        self.assertFalse(cfg["gate_a_qualified"])

    def test_causal_feature_and_expansion(self) -> None:
        states = np.arange(30 * 5, dtype=float).reshape(30, 5) / 100.0
        trajectory = [
            {"currents_a_tsc": (np.arange(14, dtype=float) + index).tolist()}
            for index in range(30)
        ]
        feature = primary.causal_feature(
            states,
            trajectory,
            decision=14,
            previous_decision=10,
            previous_q=[1.0, 0.0],
            coil_limits=np.full(14, 100.0),
        )
        self.assertEqual(feature.shape, (42,))
        row = {"feature": feature, "q": np.asarray([1.5, 0.0]),
               "previous_q": np.asarray([1.0, 0.0])}
        expanded = primary._expanded_row(row)
        self.assertEqual(expanded.shape, (133,))
        np.testing.assert_array_equal(expanded[42:49], [1.5, 0.0, 2.25, 0.0, 0.0, 0.5, 0.0])

    def test_primary_and_independent_ridge_are_exact(self) -> None:
        bank = _synthetic_bank()
        pairs = sorted({row["pair_id"] for row in bank})[:7]
        primary_model = primary.fit_models(bank, pairs, ridge=1e-4)
        independent_model = independent._fit(bank, pairs, 1e-4)
        difference = independent._maximum_difference(
            primary._model_serializable(primary_model), independent._serial(independent_model)
        )
        self.assertLessEqual(difference, 1e-12)
        prediction = primary.predict_row(primary_model, bank[0]["intervals"][0])
        self.assertEqual(prediction.shape, (4, 5))
        self.assertTrue(np.all(np.isfinite(prediction)))

    def test_nested_tube_and_support_are_whole_pair(self) -> None:
        bank = _synthetic_bank()
        pairs = sorted({row["pair_id"] for row in bank})
        training = pairs[1:]
        primary_tube, primary_evidence = primary._nested_tube(bank, training, ridge=1e-4)
        independent_tube, independent_evidence = independent._tube(bank, training, 1e-4)
        self.assertEqual(len(primary_evidence), 7)
        self.assertEqual(primary_evidence, independent_evidence)
        for left, right in zip(primary_tube, independent_tube):
            np.testing.assert_allclose(left, right, rtol=0.0, atol=1e-12)
        support_primary = primary._support_for_fold(
            bank, training, pairs[0], multiplier=1.5
        )
        support_independent = independent._support(bank, training, pairs[0], 1.5)
        self.assertLessEqual(
            independent._maximum_difference(support_primary, support_independent), 1e-12
        )

    def test_innovation_update_and_fail_closed_formal(self) -> None:
        bank = _synthetic_bank()[:1]
        model = primary.fit_models(_synthetic_bank(), [f"pair_{i}" for i in range(7)], ridge=1e-4)
        cold = primary._cold_predictions(model, bank)
        tube = [np.full((count, 5), 10.0) for count in (4, 4, 4, 15)]
        adapted, clipping = primary._adapt_predictions(bank, cold, tube)
        self.assertEqual(clipping, 0)
        self.assertEqual(len(adapted[bank[0]["trajectory_id"]]), 4)
        states = np.zeros((36, 5))
        tubes = np.zeros_like(states)
        passed, violation, _ = primary._robust_formal(
            states, tubes, deadline=25, endpoint=35,
            cfg=json.loads(CONFIG.read_text(encoding="utf-8")),
        )
        self.assertTrue(passed)
        self.assertEqual(violation, 0.0)
        tubes[:, 0] = 2.0
        passed, violation, _ = primary._robust_formal(
            states, tubes, deadline=25, endpoint=35,
            cfg=json.loads(CONFIG.read_text(encoding="utf-8")),
        )
        self.assertFalse(passed)
        self.assertGreater(violation, 0.0)

    def test_independent_does_not_import_primary_implementation(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r23_causal_online_innovation_receding_horizon_preflight as",
            source,
        )


if __name__ == "__main__":
    unittest.main()
