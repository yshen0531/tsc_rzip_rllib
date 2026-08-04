import copy
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
    stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight as r1a,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1r14r1a_quantization_margin_preflight_v1.json"
R1_CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1r14r1_pooled_mixed_basis_preflight_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S24D1R14R1A_QUANTIZATION_MARGIN_PREFLIGHT_DESIGN.md"


class Stage42R3C3T13S24D1R14R1ATests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.r1_cfg = json.loads(R1_CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_document_validate(self):
        r1a._validate_design(self.cfg)
        self.assertEqual(r1a._sha256(DESIGN), self.cfg["design_document_sha256"])

    def test_fixed_matrix_is_exact_single_column_scale(self):
        result = r1a._fixed_matrix(self.cfg, self.r1_cfg)
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["matrix_float64_le_c_sha256"],
            "c8cd62c00c1f60b46312927789659657dc8cc35717533193433b0e398c1ec94c",
        )
        base = np.asarray(self.r1_cfg["selected_requested_coordinate_matrix_columns"])
        selected = np.asarray(self.cfg["selected_requested_coordinate_matrix_columns"])
        self.assertTrue(np.array_equal(base[:, [0, 1, 3]], selected[:, [0, 1, 3]]))
        self.assertTrue(np.array_equal(base[:, 2] * 1.275, selected[:, 2]))

    def test_scale_column_or_gate_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["repair_contract"]["fixed_scale"] = 1.30
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["repair_contract"]["scaled_column_index"] = 1
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["static_issue_contract"]["maximum_relative_off_basis_residual"] = 0.14
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaisesRegex(ValueError, "frozen design changed"):
                r1a._validate_design(changed)

    def test_grid_is_disclosed_but_not_reexecuted(self):
        repair = self.cfg["repair_contract"]
        self.assertTrue(repair["selection_grid_is_disclosed_development_only"])
        self.assertFalse(repair["grid_reexecution_in_r1a_allowed"])

    def test_scope_is_zero_tsc_and_r2_design_only(self):
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertEqual(execution["plant_steps_executed"], 0)
        self.assertFalse(execution["controller_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertTrue(self.cfg["scientific_scope"]["pass_authorizes_r2_design_only"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_launchers_force_server_virtualenv_and_no_ray(self):
        shell = (ROOT / "scripts" / "stage4_2r3c3t13s24d1r14r1a_shell_common.sh").read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r1a_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell)
        self.assertIn("zero controller/plant/Ray/gotsc/TSC", common)
        self.assertNotIn("ray start", common.lower())


if __name__ == "__main__":
    unittest.main()
