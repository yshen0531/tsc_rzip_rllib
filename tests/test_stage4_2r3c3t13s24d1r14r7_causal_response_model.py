from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_causal_response_model as primary
from docs.codex.audit_tools import stage4_2r3c3t13s24d1r14r7_independent_forensics as independent
from tsc_rzip_rllib.control import causal_response_model as crm


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r7_causal_response_model_v1.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R7_CAUSAL_RESPONSE_MODEL_DESIGN.md"


class Stage42R3C3T13S24D1R14R7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_design_hash(self):
        primary._validate_config(copy.deepcopy(self.cfg))
        independent._validate_frozen_contract(copy.deepcopy(self.cfg))
        self.assertEqual(primary._sha256(DESIGN), self.cfg["design_document_sha256"])
        self.assertEqual(len(crm.candidates(self.cfg)), 27)

    def test_gate_and_timing_mutations_fail_closed(self):
        changed = copy.deepcopy(self.cfg)
        changed["gates"]["maximum_relative_l2_error"] = 0.751
        with self.assertRaises(ValueError):
            primary._validate_config(changed)
        with self.assertRaises(ValueError):
            independent._validate_frozen_contract(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaises(ValueError):
            primary._validate_config(changed)

    def test_zero_tsc_and_no_rl_boundary(self):
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertEqual(execution["plant_steps_executed"], 0)
        self.assertFalse(execution["controller_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_kernel_model_enforces_kinematics(self):
        rng = np.random.default_rng(42)
        items = []
        for context in range(8):
            descriptor = rng.normal(size=29)
            for sign in (-1, 1):
                for direction in range(4):
                    dynamic = np.column_stack((
                        np.full(4, 0.01 * sign * (direction + 1) + descriptor[0] * 1e-4),
                        np.full(4, -0.005 * sign * (direction + 1)),
                        np.full(4, 0.001 * context),
                    ))
                    response = np.zeros((4, 5))
                    response[:, 2:5] = dynamic
                    response[:, 0] = np.cumsum(dynamic[:, 0]) / 30.0
                    response[:, 1] = np.cumsum(dynamic[:, 1]) / 30.0
                    items.append({
                        "response_id": f"{context}:{sign}:{direction}",
                        "pair_id": f"pair{context // 2}", "history_member": "plus_first" if context % 2 == 0 else "minus_first",
                        "context_id": str(context), "issue_task_step": 10,
                        "sign": sign, "direction_index": direction,
                        "descriptor": descriptor.tolist(), "response": response.tolist(),
                    })
        candidate = crm.Candidate(2, 1.0, 0.001)
        model = crm.fit_model(items, candidate, self.cfg)
        predicted = crm.predict_item(model, items[0], self.cfg)
        self.assertTrue(np.all(np.isfinite(predicted)))
        self.assertTrue(np.allclose(predicted[:, 0], np.cumsum(predicted[:, 2]) / 30.0))
        self.assertTrue(np.allclose(predicted[:, 1], np.cumsum(predicted[:, 3]) / 30.0))

    def test_zero_prediction_cannot_pass_response_gate(self):
        actual = np.ones((3, 5)) * 0.01
        item = {"response_id": "x", "context_id": "c", "pair_id": "p", "history_member": "h", "issue_task_step": 10, "sign": 1, "direction_index": 0, "response": actual.tolist()}
        row = crm.prediction_row(item, np.zeros_like(actual), self.cfg)
        self.assertFalse(row["passed"])
        self.assertAlmostEqual(row["relative_l2_error"], 1.0)

    def test_independent_is_structurally_separate(self):
        source = inspect.getsource(independent)
        self.assertNotIn("causal_response_model as crm", source)
        self.assertNotIn("stage4_2r3c3t13s24d1r14r7_causal_response_model as", source)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            independent._loads('{"x": 1, "x": 2}')

    def test_launchers_pin_server_virtualenv_and_no_tsc(self):
        shell = (ROOT / "scripts/stage4_2r3c3t13s24d1r14r7_shell_common.sh").read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r7_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell)
        self.assertIn("zero controller/plant/Ray/gotsc/TSC", common)
        self.assertNotIn("ray start", common.lower())
        self.assertNotIn("--backend ray", common.lower())


if __name__ == "__main__":
    unittest.main()
