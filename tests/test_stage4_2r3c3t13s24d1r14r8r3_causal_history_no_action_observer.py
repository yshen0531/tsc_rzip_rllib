from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import numpy as np

from tsc_rzip_rllib.control import causal_history_no_action_observer as observer
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer.json"


class CausalHistoryNoActionObserverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def _signals(self, length: int = 24):
        visible = np.zeros((length, 5), dtype=float)
        visible[:, 2] = 0.2 + 0.001 * np.arange(length)
        visible[:, 3] = -0.1 + 0.002 * np.arange(length)
        visible[:, 4] = 0.3 - 0.003 * np.arange(length)
        visible[0, :2] = (1.0, -0.5)
        scales = np.asarray(self.cfg["bank_contract"]["visible_scales"], dtype=float)
        dt = float(self.cfg["bank_contract"]["dt_s"])
        visible[1:, 0] = visible[0, 0] + np.cumsum(visible[1:, 2]) * dt * scales[2] / scales[0]
        visible[1:, 1] = visible[0, 1] + np.cumsum(visible[1:, 3]) * dt * scales[3] / scales[1]
        actions = np.arange((length - 1) * 14, dtype=float).reshape(length - 1, 14) / 1000.0
        currents = np.arange(length * 14, dtype=float).reshape(length, 14)
        return visible, actions, currents

    def _feature(self):
        visible, actions, currents = self._signals()
        return observer.causal_feature(
            visible, actions, currents, (0.01, -0.02, 1000.0), 10, self.cfg
        )

    def test_contract_and_self_test(self):
        contract.validate_config(self.cfg)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["feature_shape"], [353])
        self.assertEqual(result["candidate_count"], 48)

    def test_contract_rejects_candidate_mutation(self):
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["pca_ranks"][-1] = 48
        with self.assertRaisesRegex(ValueError, "frozen contract"):
            contract.validate_config(changed)

    def test_candidate_family_is_exact(self):
        values = observer.candidates(self.cfg)
        self.assertEqual(len(values), 48)
        self.assertEqual({value.family for value in values}, {"linear", "rbf"})
        self.assertEqual({value.pca_rank for value in values}, {8, 16, 24, 32})

    def test_feature_uses_only_origin_prefix(self):
        visible, actions, currents = self._signals()
        first = observer.causal_feature(
            visible, actions, currents, (0.01, -0.02, 1000.0), 10, self.cfg
        )
        visible[11:] += 1e6
        actions[10:] += 1e6
        currents[11:] += 1e6
        second = observer.causal_feature(
            visible, actions, currents, (0.01, -0.02, 1000.0), 10, self.cfg
        )
        np.testing.assert_array_equal(first, second)

    def test_feature_excludes_action_at_origin(self):
        visible, actions, currents = self._signals()
        first = self._feature()
        actions[10] += 12345.0
        second = observer.causal_feature(
            visible, actions, currents, (0.01, -0.02, 1000.0), 10, self.cfg
        )
        np.testing.assert_array_equal(first, second)

    def test_target_and_kinematic_reconstruction(self):
        visible, _, _ = self._signals()
        delta = observer.target_delta(visible, 10, self.cfg)
        forecast = observer.forecast_from_delta(
            {"origin_visible": visible[10]}, delta, self.cfg
        )
        np.testing.assert_allclose(forecast, visible[11:23], rtol=0.0, atol=1e-14)

    def test_linear_fit_and_prediction_are_finite(self):
        generator = np.random.default_rng(21)
        items = []
        for index in range(40):
            feature = generator.normal(size=353)
            origin = np.asarray([0.1, -0.2, 0.01, -0.02, 0.3]) + index * 1e-5
            delta = np.column_stack(
                (
                    np.arange(1, 13) * feature[0] * 1e-4,
                    np.arange(1, 13) * feature[1] * 1e-4,
                    np.arange(1, 13) * feature[2] * 1e-4,
                )
            )
            base = {
                "row_id": f"row{index:02d}",
                "pair_id": f"pair{index // 4:02d}",
                "history_member": "minus_first" if index % 2 else "plus_first",
                "origin_task_step": 10,
                "prescribed_issue": True,
                "feature": feature,
                "origin_visible": origin,
                "target_delta": delta,
            }
            base["future_visible"] = observer.forecast_from_delta(base, delta, self.cfg)
            items.append(base)
        candidate = observer.Candidate("linear", 8, 0.0, 0.001)
        model = observer.fit_model(items, candidate, self.cfg)
        predictions = observer.predict_model(model, items[:3], self.cfg)
        self.assertEqual(len(predictions), 3)
        self.assertTrue(all(value.shape == (12, 5) for value in predictions))
        self.assertTrue(all(np.all(np.isfinite(value)) for value in predictions))

    def test_prediction_row_and_tube(self):
        visible, _, _ = self._signals()
        item = {
            "row_id": "row",
            "pair_id": "pair",
            "history_member": "minus_first",
            "origin_task_step": 10,
            "prescribed_issue": True,
            "future_visible": visible[11:23],
        }
        passed = observer.prediction_row(item, visible[11:23], self.cfg)
        self.assertTrue(passed["passed"])
        failed_prediction = visible[11:23].copy()
        failed_prediction[0, 2] += 0.1001
        failed = observer.prediction_row(item, failed_prediction, self.cfg)
        self.assertFalse(failed["passed"])
        tube = observer.tube_from_rows([passed, failed], self.cfg)
        self.assertEqual(tube.shape, (12, 5))
        self.assertGreater(tube[0, 2], 0.01)

    def test_routes_are_frozen(self):
        self.assertEqual(
            contract.route_for(False, self.cfg),
            "CAUSAL_HISTORY_NO_ACTION_OBSERVER_FAIL_FRESH_IDENTIFICATION_REQUIRED",
        )
        self.assertEqual(
            contract.route_for(True, self.cfg),
            "CAUSAL_HISTORY_NO_ACTION_OBSERVER_PASS_COMBINED_ADAPTATION_FREEZE_REQUIRED",
        )

    def test_independent_does_not_import_primary_observer_algorithms(self):
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r3_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("causal_history_no_action_observer as observer", source)
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer as r8r3_primary",
            source,
        )
        self.assertIn("def _all_predictions", source)
        self.assertIn("def _source_rows", source)

    def test_launcher_uses_server_virtual_environment(self):
        common = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r3_shell_common.sh"
        ).read_text(encoding="utf-8")
        launcher = (
            ROOT
            / "scripts/run_stage4_2r3c3t13s24d1r14r8r3_causal_history_no_action_observer.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", common)
        self.assertIn("R8R3_R8R2_OUTPUT", common)
        self.assertIn("STAGE4_2R3C3T13S24D1R14R8R3_PYTHON", launcher)


if __name__ == "__main__":
    unittest.main()
