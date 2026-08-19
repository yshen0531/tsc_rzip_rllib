from __future__ import annotations

import copy
import json
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2z10_five_context_model as model


class ID2Z10Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(model.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_capacity_and_gates(self) -> None:
        model.require(self.stage)
        self.assertEqual(model.base.sha256(model.CONFIG), model.CONFIG_SHA256)
        self.assertEqual(self.stage["data_contract"]["independent_causal_contexts"], 5)
        self.assertEqual(self.stage["data_contract"]["fit_weight_windows"], 25)
        self.assertEqual(self.stage["candidate_specs"][1]["hidden_size"], 4)

    def test_load_has_five_whole_contexts_and_valid_horizons(self) -> None:
        stage, contexts = model.load()
        self.assertEqual(tuple(x.context_id for x in contexts), model.CONTEXT_IDS)
        self.assertEqual([len(x.horizons) for x in contexts], [20, 16, 12, 16, 12])
        for context in contexts:
            terminal = stage["terminal_state_indices_by_context"][context.context_id]
            self.assertTrue(all(index in [context.decision + h for h in context.horizons]
                                for index in terminal))
            self.assertTrue(all(row["passed"] for row in context.rows.values()))

    def test_mutation_fails_closed(self) -> None:
        for path, value in ((["history_steps"], 16),
                            (["candidate_specs", 1, "hidden_size"], 8),
                            (["selection_gates", "maximum_r_p95_m"], 0.001),
                            (["data_contract", "independent_causal_contexts"], 4)):
            changed = copy.deepcopy(self.stage); cursor = changed
            for key in path[:-1]: cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(model.base.InputIntegrityError): model.require(changed)

    def test_action_basis_and_fold_models_are_finite(self) -> None:
        _, contexts = model.load(); basis = model.base.action_basis(contexts)
        self.assertEqual(np.linalg.matrix_rank(basis), 2)
        for held in contexts:
            train = [x for x in contexts if x.context_id != held.context_id]
            fitted = model.base.fit_backbone(train)
            for arm in ("b4", "f4", "b2f2", "f2b2"):
                self.assertTrue(np.isfinite(
                    model.base.predict_backbone(fitted, held, arm)).all())

    def test_bounded_comparison_reports_five_folds(self) -> None:
        result, artifact = model.execute(model.CONFIG, "test-revision")
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)
        self.assertEqual(result["calibration_or_holdout_records_read"], 0)
        self.assertEqual(len(result["candidate_results"]), 2)
        self.assertTrue(all(len(x["folds"]) == 5 for x in result["candidate_results"]))
        self.assertEqual(artifact is not None, result["passed"])

    def test_launcher_is_zero_tsc_and_audited(self) -> None:
        text = (model.ROOT / "run_rgeo_zgeo_1ms_id2z10_five_context_model.sh").read_text()
        self.assertIn("deterministic_replay_audit.json", text)
        self.assertNotIn("gotsc", text.lower())


if __name__ == "__main__":
    unittest.main()
