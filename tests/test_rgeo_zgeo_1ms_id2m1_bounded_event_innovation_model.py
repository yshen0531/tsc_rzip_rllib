import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


m1 = load("id2m1_primary", SCRIPTS / "rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.py")
auditor = load("id2m1_auditor", SCRIPTS / "rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model_independent.py")


class ID2M1Tests(unittest.TestCase):
    def test_frozen_identity_and_candidate_cap(self):
        stage = m1.load_stage()
        self.assertEqual(m1.sha256(m1.CONFIG), m1.CONFIG_SHA256)
        self.assertEqual(tuple(stage["model"]["candidates"]), m1.CANDIDATES)
        self.assertEqual(len(m1.CANDIDATES), 2)
        self.assertEqual((stage["new_tsc_calls"], stage["reset_calls"], stage["plant_advances"]), (0, 0, 0))

    def test_forbidden_data_and_controls(self):
        stage = m1.load_stage()
        self.assertFalse(stage["data_use"]["id2m0_predictions_as_training_labels"])
        for key in ("id2i1_records_allowed", "id2j0_records_allowed", "id2c2_records_allowed",
                    "calibration_records_allowed", "holdout_records_allowed"):
            self.assertEqual(stage["data_use"][key], 0)
        for key in ("controller_authorized", "mpc_authorized", "authority_authorized", "recovery_authorized",
                    "crossing_authorized", "adaptation_authorized", "rl_authorized"):
            self.assertFalse(stage["data_use"][key])

    def test_action_event_feature_width_and_dwell(self):
        stage = m1.load_stage()
        l1_stage, data = m1.load_inputs(stage)
        cell = data.cells[0]
        features = m1.action_event_features(cell, data, stage)
        self.assertEqual(features.shape, (34, 78))
        self.assertTrue(np.all(np.isfinite(features)))
        self.assertEqual(m1._dwell_age(cell.issued, 0), 1)
        self.assertGreaterEqual(m1._dwell_age(cell.issued, 17), 1)

    def test_innovation_is_current_causal_and_fixed_dimension(self):
        stage = m1.load_stage()
        _, data = m1.load_inputs(stage)
        cell = data.cells[0]
        current = m1.observable_innovation(cell, data, 16)
        self.assertEqual(current.shape, (12,))
        feature = m1.feature_matrix(cell, data, stage, m1.CANDIDATES[1], context_origin=16)
        self.assertTrue(np.array_equal(feature[:16, -12:], np.zeros((16, 12))))
        self.assertTrue(np.allclose(feature[17, -12:], 0.8 * feature[16, -12:]))

    def test_labels_cannot_enter_feature_api(self):
        stage = m1.load_stage()
        _, data = m1.load_inputs(stage)
        cell = data.cells[0]
        original = m1.feature_matrix(cell, data, stage, m1.CANDIDATES[0])
        cell.group_id = "changed-evaluator-label"
        cell.direction = "changed-evaluator-label"
        cell.sign = "changed-evaluator-label"
        self.assertTrue(np.array_equal(original, m1.feature_matrix(cell, data, stage, m1.CANDIDATES[0])))

    def test_model_fit_is_finite_and_nominal_is_separate(self):
        stage = m1.load_stage()
        l1_stage, data = m1.load_inputs(stage)
        held = set(l1_stage["folds"][0]["held_histories"])
        train = [cell for cell in data.cells if cell.group_id not in held]
        model = m1.fit_model(m1.CANDIDATES[0], train, data, stage)
        self.assertEqual(model.nominal.shape, (34, 3))
        self.assertEqual(model.coefficients.shape, (78, 3))
        self.assertTrue(np.all(np.isfinite(model.coefficients)))

    def test_full_comparison_emits_at_most_one_model(self):
        result, payload = m1.compute(source_revision="test-revision")
        self.assertEqual(set(result["comparison"]["candidates"]), set(m1.CANDIDATES))
        self.assertEqual(result["tsc_calls"], 0)
        self.assertEqual(result["holdout_records_read"], 0)
        if result["passed"]:
            self.assertIsNotNone(payload)
            self.assertEqual(payload["selected_candidate"], result["selected_candidate"])
        else:
            self.assertIsNone(payload)

    def test_independent_recomputation_accepts_scientific_pass_or_fail(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            output = Path(folder) / "m1"
            result = m1.execute(m1.CONFIG, "test-revision", output)
            value = auditor.audit(m1.CONFIG, "test-revision", output)
            self.assertTrue(value["audit_passed"])
            self.assertEqual(value["primary_scientific_passed"], result["passed"])

    def test_non_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            target = Path(folder) / "result.json"
            m1.write_new(target, {"x": 1})
            with self.assertRaises(FileExistsError):
                m1.write_new(target, {"x": 2})

    def test_launcher_has_no_tsc_entrypoint(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2m1_bounded_event_innovation_model.sh").read_text(encoding="utf-8")
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("cleanup", text.lower())


if __name__ == "__main__":
    unittest.main()
