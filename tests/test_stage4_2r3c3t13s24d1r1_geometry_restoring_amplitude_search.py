import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search as r1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search_v1.json"
S23R1_CONFIG = ROOT / "configs" / "stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S24D1R1_GEOMETRY_RESTORING_AMPLITUDE_SEARCH_DESIGN.md"


class Stage42R3C3T13S24D1R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.s23r1_cfg = json.loads(S23R1_CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_document_validate(self):
        r1._validate_design(self.cfg)
        self.assertEqual(r1._sha256(DESIGN), self.cfg["design_document_sha256"])

    def test_grid_is_exact_decimal_and_inclusive(self):
        grid = r1._grid(self.cfg)
        self.assertEqual(len(grid), 56)
        self.assertEqual(grid[0], Decimal("0.225"))
        self.assertEqual(grid[-1], Decimal("0.500"))
        self.assertTrue(all(b - a == Decimal("0.005") for a, b in zip(grid, grid[1:])))

    def test_grid_refinement_or_gate_change_is_rejected(self):
        changed = copy.deepcopy(self.cfg)
        changed["search_contract"]["grid_step_decimal"] = "0.0025"
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            r1._validate_design(changed)
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["minimum_desired_applied_current_cosine"] = 0.97
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            r1._validate_design(changed)

    def test_canonical_pattern_is_orientation_invariant(self):
        self.assertEqual(r1._canonical_pattern([1, 1, -1, -1]), "++--")
        self.assertEqual(r1._canonical_pattern([-1, -1, 1, 1]), "++--")
        self.assertEqual(r1._canonical_pattern([1, -1, -1, 1]), "+--+")

    def test_selection_stops_at_first_feasible_value(self):
        calls = []
        grid = (Decimal("0.225"), Decimal("0.230"), Decimal("0.235"))

        def evaluate(pattern, amplitude):
            calls.append((pattern, amplitude))
            return {"amplitude_decimal": str(amplitude), "passed": amplitude >= Decimal("0.230")}

        selected, rows = r1._select_first_feasible("++--", grid, evaluate)
        self.assertEqual(selected, Decimal("0.230"))
        self.assertEqual(len(rows), 2)
        self.assertEqual([value for _, value in calls], list(grid[:2]))

    def test_replay_config_uses_only_selected_fixed_map(self):
        amplitudes = {
            "++++": Decimal("0.250"), "+-+-": Decimal("0.250"),
            "++--": Decimal("0.300"), "+--+": Decimal("0.315"),
        }
        replay = r1._replay_config(self.s23r1_cfg, self.cfg, amplitudes)
        self.assertEqual(
            replay["schedule_contract"]["canonical_pattern_amplitudes"],
            {"++++": 0.25, "+-+-": 0.25, "++--": 0.3, "+--+": 0.315},
        )

    def test_scope_remains_zero_tsc_and_sentinel_only(self):
        self.assertEqual(self.cfg["execution_contract"]["new_raw_count"], 0)
        self.assertFalse(self.cfg["execution_contract"]["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["pass_authorizes_full_campaign"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("zero-new-TSC", text)
        self.assertIn("0.225, 0.230, 0.235", text)
        self.assertIn("0.24", text)

    def test_launchers_use_server_virtualenv_and_zero_tsc_path(self):
        common = (ROOT / "run_stage4_2r3c3t13s24d1r1_common.sh").read_text(encoding="utf-8")
        shell_common = (ROOT / "scripts" / "stage4_2r3c3t13s24d1r1_shell_common.sh").read_text(encoding="utf-8")
        offline = (ROOT / "run_stage4_2r3c3t13s24d1r1_offline.sh").read_text(encoding="utf-8")
        self.assertIn("zero plant/controller/Ray/gotsc/TSC", common)
        self.assertIn("stage4_2r3c3t13s24d1r1_geometry_restoring_amplitude_search.py", common)
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell_common)
        self.assertNotIn("ray start", common.lower())
        self.assertIn("run_stage4_2r3c3t13s24d1r1_common.sh", offline)


if __name__ == "__main__":
    unittest.main()
