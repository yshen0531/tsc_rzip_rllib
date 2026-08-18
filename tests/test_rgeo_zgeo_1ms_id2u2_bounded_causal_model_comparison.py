from __future__ import annotations

import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rgeo_zgeo_1ms_id2u2_bounded_causal_model_comparison as u2  # noqa: E402


class ID2U2ModelComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage = u2.load_stage()
        cls.data = u2.load_dataset(cls.stage)

    def test_frozen_identity_and_zero_plant_contract(self) -> None:
        self.assertEqual(u2.sha256(u2.CONFIG), u2.CONFIG_SHA256)
        self.assertEqual(self.stage["candidate_order"], list(u2.CANDIDATES))
        self.assertEqual(self.stage["fit_and_execution_counts"]["new_tsc_calls"], 0)
        self.assertEqual(self.stage["fit_and_execution_counts"]["reset_calls"], 0)
        self.assertEqual(self.stage["fit_and_execution_counts"]["plant_advances"], 0)

    def test_only_four_development_families_are_loaded(self) -> None:
        self.assertEqual(self.data.families, ("u00", "u02", "u04", "u06"))
        self.assertEqual(len(self.data.cells), 20)
        self.assertEqual(sum(cell.kind == "baseline" for cell in self.data.cells), 4)
        self.assertEqual(sum(cell.kind == "probe" for cell in self.data.cells), 16)
        self.assertEqual(self.data.action_basis.shape, (3, 14))

    def test_every_probe_has_exact_matched_prefix_and_eight_step_window(self) -> None:
        for cell in self.data.cells:
            baseline = self.data.baselines[cell.family_id]
            if cell.kind == "probe":
                self.assertTrue(np.array_equal(cell.states[: cell.probe_issue + 1], baseline.states[: cell.probe_issue + 1]))
                self.assertTrue(np.array_equal(cell.issued[: cell.probe_issue], baseline.issued[: cell.probe_issue]))
            self.assertLessEqual(cell.probe_issue + 8, 40)

    def test_local_causal_prefix_feature_changes_with_recent_history(self) -> None:
        cell = next(cell for cell in self.data.cells if cell.cell_id == "u00__baseline")
        feature = u2.causal_prefix_feature(cell, 24, self.data, self.stage)
        states = cell.states.copy()
        states[22, 0] += 1.0e-4
        changed = replace(cell, states=states)
        changed_feature = u2.causal_prefix_feature(changed, 24, self.data, self.stage)
        self.assertFalse(np.array_equal(feature, changed_feature))

    def test_local_candidate_predicts_all_held_cells_without_using_labels(self) -> None:
        for held in self.data.families:
            train = [family for family in self.data.families if family != held]
            model = u2.LocalEventModel(train, self.data, self.stage)
            baseline = self.data.baselines[held]
            base_prediction = model.predict(baseline, baseline.probe_issue)
            self.assertEqual(base_prediction.shape, (8, 3))
            self.assertTrue(np.all(np.isfinite(base_prediction)))
            for cell in self.data.cells:
                if cell.family_id == held and cell.kind == "probe":
                    prediction = model.predict(cell, cell.probe_issue)
                    self.assertEqual(prediction.shape, (8, 3))
                    self.assertTrue(np.all(np.isfinite(prediction)))

    def test_local_metrics_have_frozen_shapes(self) -> None:
        held = "u00"
        model = u2.LocalEventModel([family for family in self.data.families if family != held], self.data, self.stage)
        metrics = u2.evaluate(model, held, self.data, self.stage)
        self.assertEqual(len(metrics["support"]), 4)
        self.assertEqual(len(metrics["peak_cosines"]), 4)
        self.assertEqual(np.asarray(metrics["endpoint_p95_abs_by_horizon"]).shape, (8, 3))
        self.assertEqual(len(metrics["maximum_unique_event_abs_error"]), 3)

    def test_gru_residual_smoke_is_persistent_and_finite(self) -> None:
        stage = copy.deepcopy(self.stage)
        stage["stable_local_event_gru_residual"]["epochs"] = 1
        stage["stable_local_event_gru_residual"]["seeds"] = [1701]
        held = "u00"
        train = [family for family in self.data.families if family != held]
        model = u2.fit_gru(train, self.data, stage)
        cell = self.data.baselines[held]
        prediction = model.predict(cell, cell.probe_issue)
        self.assertEqual(prediction.shape, (8, 3))
        self.assertTrue(np.all(np.isfinite(prediction)))
        states = cell.states.copy()
        states[8, 0] += 1.0e-4
        changed = replace(cell, states=states)
        changed_prediction = model.predict(changed, changed.probe_issue)
        self.assertFalse(np.array_equal(prediction, changed_prediction))

    def test_support_abstention_cannot_pass_a_fold(self) -> None:
        held = "u00"
        model = u2.LocalEventModel([family for family in self.data.families if family != held], self.data, self.stage)
        metrics = u2.evaluate(model, held, self.data, self.stage)
        metrics["supported_probe_origins"] = 3
        self.assertIn("SUPPORT", u2.eligibility(metrics, model, self.stage))

    def test_launcher_keeps_primary_failure_for_independent_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_id2u2_model_comparison.sh").read_text(encoding="utf-8")
        self.assertIn('primary_rc="${primary_rc:-0}"', text)
        self.assertIn("rgeo_zgeo_1ms_id2u2_bounded_causal_model_independent.py", text)
        self.assertNotIn("gotsc", text.lower())

    def test_config_is_strict_json_and_design_hash_matches(self) -> None:
        value = json.loads(u2.CONFIG.read_text(encoding="utf-8"))
        design = ROOT / value["source"]["design"]["path"]
        self.assertEqual(u2.sha256(design), value["source"]["design"]["sha256"])


if __name__ == "__main__":
    unittest.main()
