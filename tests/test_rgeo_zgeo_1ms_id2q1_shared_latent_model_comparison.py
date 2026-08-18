import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch


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


q1 = load("id2q1_primary", SCRIPTS / "rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison.py")
auditor = load("id2q1_auditor", SCRIPTS / "rgeo_zgeo_1ms_id2q1_shared_latent_model_independent.py")


class ID2Q1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = q1.load_stage()
        cls.data = q1.load_dataset(cls.stage)

    def test_frozen_identity_and_two_candidates(self):
        self.assertEqual(q1.sha256(q1.CONFIG), q1.CONFIG_SHA256)
        self.assertEqual(list(self.stage["candidates"]), [
            "stable_shared_latent_ridge", "stable_shared_latent_gru_residual"
        ])
        self.assertEqual((self.stage["new_tsc_calls"], self.stage["reset_calls"], self.stage["plant_advances"]), (0, 0, 0))
        self.assertEqual(self.stage["shared_latent"]["actual_current_innovation_decay_per_step"], 0.8)
        self.assertEqual(self.stage["shared_latent"]["executed_action_subspace_rank"], 3)

    def test_exact_fit_data_roles(self):
        self.assertEqual(len(self.data.cells), 80)
        families = sorted({cell.group_id for cell in self.data.cells})
        self.assertEqual(len(families), 16)
        self.assertTrue(all(sum(cell.group_id == family for cell in self.data.cells) == 5 for family in families))
        self.assertTrue(all(self.stage["forbidden_sources"].values()))

    def test_action_plane_and_features(self):
        residual = max(float(np.max(np.abs((cell.issued - self.data.nominal_issued) - ((cell.issued - self.data.nominal_issued) @ self.data.action_basis.T) @ self.data.action_basis))) for cell in self.data.cells)
        self.assertLessEqual(residual, 1e-9)
        cell = next(cell for cell in self.data.cells if cell.cell_kind == "probe")
        nominal, _ = q1.nominal_training(self.data.cells)
        features = q1.step_features(cell, 16, self.data, nominal, self.stage)
        self.assertEqual(features.shape, (8, 104))
        self.assertTrue(np.all(np.isfinite(features)))
        self.assertTrue(np.allclose(features[1, 9:12], 0.8 * features[0, 9:12]))

    def test_labels_do_not_enter_feature_api(self):
        cell = next(cell for cell in self.data.cells if cell.cell_kind == "probe")
        nominal, _ = q1.nominal_training(self.data.cells)
        original = q1.step_features(cell, 16, self.data, nominal, self.stage)
        saved = (cell.group_id, cell.direction, cell.sign)
        try:
            cell.group_id = "changed-evaluator-label"
            cell.direction = "changed-evaluator-label"
            cell.sign = "changed-evaluator-label"
            self.assertTrue(np.array_equal(original, q1.step_features(cell, 16, self.data, nominal, self.stage)))
        finally:
            cell.group_id, cell.direction, cell.sign = saved

    def test_gru_hidden_state_is_causal_at_origin(self):
        q1.seed_all(123)
        module = q1.GRUResidual(15, 104, 8, np.asarray([3.0, 3.0, 2.0])).eval()
        sequence = torch.randn(1, 34, 15)
        altered = sequence.clone()
        altered[:, 17:, :] += 1000.0
        feature = torch.randn(8, 104)
        index = torch.zeros(8, dtype=torch.long)
        origin = torch.full((8,), 16, dtype=torch.long)
        with torch.no_grad():
            first = module(sequence, feature, index, origin)
            second = module(altered, feature, index, origin)
        self.assertTrue(torch.equal(first, second))

    def test_one_fold_ridge_is_finite_and_shared(self):
        held = set(self.stage["whole_family_folds"][0]["held"])
        train = [cell for cell in self.data.cells if cell.group_id not in held]
        test = [cell for cell in self.data.cells if cell.group_id in held]
        model = q1.fit_ridge(train, self.data, self.stage)
        self.assertEqual(model.coef.shape, (104, 3))
        self.assertTrue(np.all(np.isfinite(model.coef)))
        metrics = q1.evaluate(model, test, self.data, self.stage)
        self.assertEqual(metrics["probe_count"], 16)
        self.assertEqual(len(metrics["endpoint_p95_abs_by_horizon"]), 8)

    def test_independent_revision_filter_and_nonoverwrite(self):
        self.assertEqual(auditor.without_revision({"source_revision": "a", "x": 1}), {"x": 1})
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            target = Path(folder) / "result.json"
            q1.write_new(target, {"x": 1})
            with self.assertRaises(q1.IntegrityError):
                q1.write_new(target, {"x": 2})

    def test_launcher_has_no_plant_entrypoint(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2q1_shared_latent_model_comparison.sh").read_text(encoding="utf-8")
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("cleanup", text.lower())


if __name__ == "__main__":
    unittest.main()
