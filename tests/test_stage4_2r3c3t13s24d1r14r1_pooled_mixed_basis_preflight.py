import copy
import hashlib
import json
from pathlib import Path
import sys
import types
import unittest

import numpy as np

if sys.platform == "win32":
    try:
        import resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight as r1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S24D1R14R1_POOLED_MIXED_BASIS_PREFLIGHT_DESIGN.md"


class Stage42R3C3T13S24D1R14R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_document_validate(self):
        r1._validate_design(self.cfg)
        self.assertEqual(r1._sha256(DESIGN), self.cfg["design_document_sha256"])

    def test_selected_matrix_digest_is_byte_exact(self):
        matrix = self.cfg["selected_requested_coordinate_matrix_columns"]
        self.assertEqual(
            r1._matrix_digest(matrix),
            "bfe35863262ed12aac303de14341c42c701188481d412c414915a2b4eb6e4bb8",
        )
        self.assertAlmostEqual(np.max(np.abs(matrix)), 3.921547352685623)

    def test_seed_search_count_or_gate_change_is_rejected(self):
        for key, value in (
            ("seed", 140043),
            ("candidate_count", 59999),
            ("maximum_predicted_unit_column_condition", 20.0),
        ):
            changed = copy.deepcopy(self.cfg)
            changed["search_contract"][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design changed"):
                r1._validate_design(changed)

    def test_candidate_metric_reports_peak_and_unit_condition(self):
        matrices = [np.eye(4), 2.0 * np.eye(4)]
        peak, condition, rows = r1._candidate_metrics(matrices, np.eye(4))
        self.assertEqual(peak, 1.0)
        self.assertEqual(condition, 1.0)
        self.assertEqual(len(rows), 2)

    def test_scope_is_zero_tsc_and_r2_design_only(self):
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertEqual(execution["plant_steps_executed"], 0)
        self.assertFalse(execution["controller_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertTrue(self.cfg["scientific_scope"]["pass_authorizes_r2_design_only"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_online_cancel_is_not_claimed_by_static_preflight(self):
        issue = self.cfg["static_issue_contract"]
        self.assertFalse(issue["cancellation_proved_by_static_preflight"])
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("diagnostic only", text)
        self.assertIn("zero-new-TSC", text)

    def test_launchers_force_server_virtualenv_and_no_ray(self):
        shell_common = (ROOT / "scripts" / "stage4_2r3c3t13s24d1r14r1_shell_common.sh").read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r1_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell_common)
        self.assertIn("zero controller/plant/Ray/gotsc/TSC", common)
        self.assertNotIn("ray start", common.lower())


if __name__ == "__main__":
    unittest.main()
