from __future__ import annotations

import ast
import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R1_FIXED_CANDIDATE_SHORT_HORIZON_DESIGN.md"
PRIMARY = ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator.py"
INDEPENDENT = ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r1_independent_forensics.py"


class Stage42R8R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_design_and_self_test(self):
        import hashlib

        r8r1.validate_config(self.cfg)
        self.assertEqual(
            hashlib.sha256(DESIGN.read_bytes()).hexdigest(),
            self.cfg["design_document_sha256"],
        )
        self.assertTrue(r8r1.self_test(CONFIG)["passed"])
        self.assertEqual(r8r1.candidate_tuple(self.cfg), (4, 2.0, 0.1))
        self.assertEqual(self.cfg["new_tsc_rollouts"], 0)

    def test_selection_is_largest_useful_passing_horizon(self):
        rows = {h: {"passed": False} for h in (4, 6, 8, 10, 12)}
        rows[4]["passed"] = rows[6]["passed"] = True
        self.assertIsNone(r8r1.select_horizon(rows, self.cfg))
        rows[8]["passed"] = True
        self.assertEqual(r8r1.select_horizon(rows, self.cfg), 8)
        rows[10]["passed"] = rows[12]["passed"] = True
        self.assertEqual(r8r1.select_horizon(rows, self.cfg), 12)

    def test_truncation_never_shifts_origin(self):
        response = np.arange(20 * 5, dtype=float).reshape(20, 5)
        row = {"descriptor": [0.0] * 142, "response": response.tolist()}
        value = r8r1.truncate_item(row, 8)
        np.testing.assert_array_equal(np.asarray(value["response"]), response[:8])
        with self.assertRaises(ValueError):
            r8r1.truncate_item(row, 21)

    def test_outer_fit_is_fixed_once_per_pair_and_reused_across_horizons(self):
        items = []
        for pair in range(12):
            for index in range(76):
                items.append(
                    {
                        "response_id": f"p{pair:02d}_{index:02d}",
                        "pair_id": f"pair_{pair:02d}",
                        "context_id": f"pair_{pair:02d}|h{index % 2}",
                        "history_member": f"h{index % 2}",
                        "issue_task_step": 10,
                        "sign": -1 if index % 2 else 1,
                        "direction_index": index % 4,
                        "source_stage": "synthetic",
                        "action_scale": 1.0,
                        "geometry_roles": ["canonical", "operational"],
                        "descriptor": [0.0] * 142,
                        "response": np.zeros((12, 5)).tolist(),
                    }
                )
        fake_r8_cfg = {
            "gates": {},
            "model_contract": {},
            "bank_contract": {},
        }

        def fake_prediction_row(item, prediction, _cfg):
            return {"response_id": item["response_id"], "predicted_response": prediction.tolist()}

        with (
            mock.patch.object(r8r1.model, "fit_model", return_value={}) as fitted,
            mock.patch.object(r8r1.model, "predict_item", return_value=np.zeros((12, 5))) as predicted,
            mock.patch.object(r8r1.model, "prediction_row", side_effect=fake_prediction_row) as reported,
        ):
            rows, folds = r8r1.outer_prediction_rows(items, self.cfg, fake_r8_cfg)
        self.assertEqual(fitted.call_count, 12)
        self.assertEqual(predicted.call_count, 912)
        self.assertEqual(reported.call_count, 912 * 5)
        self.assertEqual(len(folds), 12)
        self.assertEqual({key: len(value) for key, value in rows.items()}, {4: 912, 6: 912, 8: 912, 10: 912, 12: 912})
        self.assertTrue(all(fold["fixed_candidate"] == self.cfg["fixed_candidate"] for fold in folds))

    def test_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg); changed["fixed_candidate"]["pca_rank"] = 8; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["horizon_contract"]["selection_order"] = [8, 10, 12]; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["horizon_contract"]["origin_shift_allowed"] = True; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["gates"]["maximum_relative_l2_error"] = 0.8; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["formal_timing_contract"]["normal_arrival_deadline_step"] = 26; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["new_tsc_rollouts"] = 1; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["bc_dagger_or_rl_allowed"] = True; mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    r8r1.validate_config(value)

    def test_independent_model_path_is_structurally_separate(self):
        source = INDEPENDENT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        self.assertIn("stage4_2r3c3t13s24d1r14r7r2_independent_forensics", imported)
        self.assertNotIn("action_conditioned_history_response_model", imported)
        self.assertIn("independent_model._fit", source)
        self.assertIn("independent_model._predict", source)
        self.assertIn('source_state_path = paths["stage"] / "stage_state.json"', source)
        self.assertNotIn('paths["state"]', source)

    def test_primary_and_independent_are_zero_tsc_postprocessors(self):
        for path in (PRIMARY, INDEPENDENT):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import ray", source)
            self.assertNotIn("gotsc(", source)
            self.assertNotIn("plant.step", source)
        self.assertFalse(self.cfg["probe_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["mpc_validated"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
