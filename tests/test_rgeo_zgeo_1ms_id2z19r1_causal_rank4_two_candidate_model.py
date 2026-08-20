import copy
import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = ROOT / "scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.py"
AUDIT_PATH = ROOT / "scripts/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model_audit.py"
CONFIG_PATH = ROOT / "configs/rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.json"
LAUNCHER = ROOT / "run_rgeo_zgeo_1ms_id2z19r1_causal_rank4_two_candidate_model.sh"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


primary = load_module("id2z19r1_primary_test", PRIMARY_PATH)
auditor = load_module("id2z19r1_audit_test", AUDIT_PATH)


class ID2Z19R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = primary.load_stage()
        cls.data = primary.load_dataset(cls.stage)

    def test_frozen_identity_and_counts(self):
        self.assertEqual(self.stage["stage"], "ID-2Z19R1")
        self.assertEqual(tuple(self.stage["candidate_order"]), primary.CANDIDATES)
        self.assertEqual(tuple(self.stage["fit_horizons_ms"]), tuple(range(1, 9)))
        self.assertEqual(tuple(self.stage["qualification_horizons_ms"]), (1, 2, 4, 8))
        counts = self.stage["fit_and_execution_counts"]
        self.assertEqual(counts["candidate_count"], 2)
        self.assertEqual(counts["maximum_candidate_fold_fits"], 16)
        self.assertEqual(counts["maximum_action_blind_fold_fits"], 8)
        self.assertEqual(counts["maximum_tcn_seed_fits"], 24)
        self.assertEqual(counts["new_tsc_calls"], 0)
        self.assertEqual(counts["calibration_records_read"], 0)
        self.assertEqual(counts["blind_holdout_records_read"], 0)

    def test_full_signed_action_geometry_is_exact_rank_four(self):
        self.assertEqual(self.data.action_basis.shape, (4, 14))
        self.assertEqual(self.data.nonzero_action_rows, 432)
        self.assertGreater(self.data.action_singular_values[3], 0.4)
        self.assertLess(self.data.action_singular_values[4], 1.0e-9)
        self.assertLessEqual(self.data.action_rank4_max_l2_residual_a, 1.0e-9)
        self.assertLessEqual(self.data.action_rank4_max_component_residual_a, 1.0e-9)
        self.assertGreaterEqual(self.data.superseded_rank3_max_l2_residual_a, 0.05)

    def test_prefit_readiness_passes_without_fit(self):
        value = primary.preflight()
        self.assertTrue(value["passed"])
        self.assertEqual(value["route"], self.stage["routes"]["prefit_pass"])
        self.assertEqual(value["action_geometry"]["rank"], 4)
        self.assertEqual(value["new_tsc_calls"], 0)

    def test_future_recorded_fields_are_mutation_invariant(self):
        value = primary.causal_mutation_invariance(self.data, self.stage)
        self.assertTrue(value["passed"])
        self.assertEqual(value["future_active_actual_rzi_mutation_feature_max_abs_difference"], 0.0)
        self.assertEqual(value["future_active_actual_rzi_mutation_history_max_abs_difference"], 0.0)

    def test_future_summary_uses_candidate_targets_not_future_active(self):
        cell = self.data.cells["d00_plus"]
        reference = primary.future_summary(cell, 16, 8, self.data)
        active = cell.active.copy()
        actual = cell.actual.copy()
        states = cell.states.copy()
        active[17:] += 333.0
        actual[17:] -= 222.0
        states[17:] += np.asarray([1.0, -2.0, 3000.0])
        mutated = replace(cell, active=active, actual=actual, states=states)
        candidate = primary.future_summary(mutated, 16, 8, self.data)
        np.testing.assert_array_equal(candidate, reference)

    def test_recursive_candidate_delta_matches_recorded_semantics(self):
        for family in self.data.families:
            cell = self.data.cells[family]
            for origin in (16, 24, 32, 48, 57):
                horizon = min(8, 65 - origin)
                reconstructed = primary.candidate_future_deltas(cell, origin, horizon, self.data)
                recorded = np.asarray([
                    primary.coord(cell.targets[issue] - cell.active[issue], self.data)
                    for issue in range(origin, origin + horizon)
                ])
                np.testing.assert_allclose(reconstructed, recorded, atol=1.0e-12, rtol=0.0)

    def test_action_blind_feature_removes_all_current_and_action_coordinates(self):
        cell = self.data.cells["d00_plus"]
        memory = primary.memories(
            cell, self.data, self.stage["structured_rank4_stable_memory"]["fixed_action_memory_poles"]
        )
        blind = primary.structured_feature(cell, 24, 4, self.data, self.stage, memory, action_blind=True)
        full = primary.structured_feature(cell, 24, 4, self.data, self.stage, memory, action_blind=False)
        self.assertEqual(blind.shape, (12,))
        self.assertEqual(full.shape, (44,))
        self.assertLess(blind.size, full.size)

    def test_tcn_is_causal_at_origin(self):
        torch.manual_seed(4)
        network = primary.CausalTCNResidual(19, 4, 14, np.ones(6)).double().eval()
        history = torch.randn(1, 66, 19, dtype=torch.float64)
        changed = history.clone()
        origin = 24
        changed[:, origin + 1 :, :] += 1000.0
        family = torch.tensor([0], dtype=torch.long)
        origins = torch.tensor([origin], dtype=torch.long)
        future = torch.randn(1, 14, dtype=torch.float64)
        with torch.no_grad():
            left = network(history, family, origins, future)
            right = network(changed, family, origins, future)
        torch.testing.assert_close(left, right, rtol=0.0, atol=0.0)

    def test_tcn_selection_cannot_bypass_relative_gate_contract(self):
        selection = self.stage["selection"]
        self.assertTrue(selection["tcn_must_independently_pass_all_gates"])
        self.assertEqual(selection["minimum_tcn_worst_pair_response_improvement_fraction"], 0.1)
        self.assertEqual(selection["maximum_tcn_componentwise_critical_metric_regression_fraction"], 0.1)

    def test_ranking_is_descriptive_and_has_tie_band(self):
        evaluation = self.stage["evaluation"]
        self.assertTrue(evaluation["ranking_is_descriptive_not_eligibility"])
        self.assertGreater(evaluation["ranking_tie_band_normalized"], 0.0)
        self.assertGreater(evaluation["minimum_rz_direction_signal_m"], 0.0)

    def test_expected_oof_ledger_rows(self):
        expected = len(primary.CANDIDATES) * len(self.stage["development_family_ids"]) * 42 * 8
        self.assertEqual(expected, 9408)

    def test_auditor_is_structurally_separate_and_never_refits(self):
        text = AUDIT_PATH.read_text(encoding="utf-8")
        self.assertNotIn("import rgeo_zgeo_1ms_id2z19r1", text)
        self.assertNotIn("fit_ridge", text)
        self.assertNotIn("fit_tcn", text)
        self.assertIn("oof_predictions.json", text)

    def test_launcher_runs_audit_even_after_scientific_fail(self):
        text = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("set +e", text)
        self.assertIn("PRIMARY_STATUS=$?", text)
        self.assertIn("oof_predictions.json", text)
        self.assertIn("independent_audit", text)

    def test_no_gru_or_tsc_in_model_identity(self):
        primary_text = PRIMARY_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn("nn.gru", primary_text)
        self.assertNotIn("gotsc", primary_text)
        self.assertEqual(self.stage["fit_and_execution_counts"]["plant_advances"], 0)

    def test_json_is_strict_and_evidence_hashes_match(self):
        json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        for item in self.stage["source"].values():
            if isinstance(item, dict) and "path" in item:
                self.assertEqual(primary.sha256(ROOT / item["path"]), item["sha256"])


if __name__ == "__main__":
    unittest.main()
