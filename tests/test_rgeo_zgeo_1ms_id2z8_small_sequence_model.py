from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


model = _module(
    "id2z8", "scripts/rgeo_zgeo_1ms_id2z8_small_sequence_model.py")


class ID2Z8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(model.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_hash_candidates_and_gates(self) -> None:
        model.require(self.stage)
        self.assertEqual(model.sha256(model.CONFIG), model.CONFIG_SHA256)
        self.assertEqual(
            [row["candidate_id"] for row in self.stage["candidate_specs"]],
            ["stable_local_memory", "stable_local_memory_plus_gru4"])
        self.assertEqual(self.stage["data_contract"]["fit_weight_windows"], 15)
        self.assertEqual(
            self.stage["data_contract"]["independent_causal_contexts"], 3)
        self.assertEqual(self.stage["calibration_holdout_expert_bc_dagger_rl_weight"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        for path, value in (
                (("history_steps",), 16),
                (("candidate_specs", 0, "ridge_lambda"), 0.1),
                (("candidate_specs", 1, "hidden_size"), 8),
                (("candidate_specs", 1, "seeds"), [17]),
                (("selection_gates", "maximum_response_nrmse_each_fold"), 1.0),
                (("future_actual_current_forbidden",), False),
                (("calibration_holdout_expert_bc_dagger_rl_weight",), 1)):
            changed = copy.deepcopy(self.stage)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.assertRaises(model.InputIntegrityError):
                model.require(changed)

    def test_load_has_three_whole_contexts_and_exact_terminal_horizons(self) -> None:
        stage, contexts = model.load()
        self.assertEqual([value.context_id for value in contexts],
                         ["state49", "state53", "state57"])
        self.assertEqual([len(value.horizons) for value in contexts], [20, 16, 12])
        for context in contexts:
            self.assertEqual(context.decision + context.horizons[-1], 69)
            self.assertEqual(set(context.rows), set(stage["arm_ids"]))
            self.assertTrue(all(row["passed"] for row in context.rows.values()))
            self.assertTrue(all(row["fit_weight"] == 1
                                for row in context.rows.values()))

    def test_action_basis_is_rank_two_and_memories_are_causal(self) -> None:
        _, contexts = model.load()
        basis = model.action_basis(contexts)
        self.assertEqual(basis.shape, (14, 2))
        self.assertEqual(np.linalg.matrix_rank(basis), 2)
        memory = model.action_memory("BFHH", 12)
        self.assertEqual(memory.shape, (12, 8))
        self.assertTrue(np.allclose(memory[0, :4], [1, 1, 1, 1]))
        self.assertTrue(np.allclose(memory[0, 4:], 0))
        self.assertGreater(np.linalg.norm(memory[-1]), 0)

    def test_future_truth_does_not_enter_gru_input(self) -> None:
        _, contexts = model.load()
        basis = model.action_basis(contexts)
        context = contexts[1]
        backbone = np.zeros((len(context.horizons), 3))
        before = model.history_future_input(context, "b2f2", basis, backbone)
        changed = copy.deepcopy(context)
        for state in changed.rows["b2f2"]["states"][context.decision + 1:]:
            state["r_geo_m"] += 123.0
            state["z_geo_m"] -= 456.0
            state["ip_a"] += 789.0
            state["actual_current_decimal_a_tsc"] = ["999"] * 14
        after = model.history_future_input(changed, "b2f2", basis, backbone)
        self.assertTrue(np.array_equal(before, after))

    def test_fold_local_backbone_uses_only_two_contexts(self) -> None:
        _, contexts = model.load()
        for held in contexts:
            train = [value for value in contexts
                     if value.context_id != held.context_id]
            fitted = model.fit_backbone(train)
            self.assertEqual(fitted["weights"].shape, (16, 3))
            self.assertLessEqual(fitted["feature_rank"], 16)
            for arm in ("b4", "f4", "b2f2", "f2b2"):
                prediction = model.predict_backbone(fitted, held, arm)
                self.assertEqual(prediction.shape, (len(held.horizons), 3))
                self.assertTrue(np.isfinite(prediction).all())

    def test_full_comparison_is_bounded_and_reports_all_folds(self) -> None:
        result, artifact = model.execute(model.CONFIG, "test-revision")
        self.assertIn(result["route"], set(self.stage["routes"].values()))
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)
        self.assertEqual(result["calibration_or_holdout_records_read"], 0)
        self.assertEqual(result["controller_or_optimizer_runs"], 0)
        self.assertEqual(len(result["candidate_results"]), 2)
        for candidate in result["candidate_results"]:
            self.assertEqual(len(candidate["folds"]), 3)
            self.assertEqual(
                {fold["context_id"] for fold in candidate["folds"]},
                {"state49", "state53", "state57"})
            self.assertTrue(np.isfinite(candidate["mean_response_nrmse"]))
        self.assertEqual(artifact is not None, result["passed"])

    def test_launcher_runs_primary_and_deterministic_audit(self) -> None:
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z8_small_sequence_model.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z8_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z8_OUTPUT", launcher)
        self.assertIn("small_sequence_model_audit.py", launcher)
        self.assertNotIn("gotsc", launcher.lower())


if __name__ == "__main__":
    unittest.main()
