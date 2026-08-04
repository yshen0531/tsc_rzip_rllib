from __future__ import annotations

import copy
import inspect
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
    stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight as primary,
    stage4_2r3c3t13s24d1r14r5_independent_forensics as independent,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r5_global_direction0_gain_preflight_v1.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R5_GLOBAL_DIRECTION0_GAIN_PREFLIGHT_DESIGN.md"
R4_CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r4_time_shifted_sign_split_sentinel_370ms.json"


class Stage42R3C3T13S24D1R14R5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.r4_cfg = json.loads(R4_CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_hash_and_both_validators(self):
        primary._validate_design(copy.deepcopy(self.cfg))
        independent._validate_frozen_contract(copy.deepcopy(self.cfg))
        self.assertEqual(primary._sha256(DESIGN), self.cfg["design_document_sha256"])
        self.assertEqual(
            self.cfg["design_document_sha256"],
            "8383ef5e0cf7678adcf9f3c776fbe925e7b57b8e6e9398eae13bff35e1f5b400",
        )

    def test_candidate_is_exact_global_column0_scale(self):
        result = primary._fixed_matrix(self.cfg, self.r4_cfg)
        self.assertTrue(result["passed"])
        self.assertEqual(result["fixed_scale"], 1.5)
        self.assertEqual(result["scaled_column_index"], 0)
        source = np.asarray(result["source_matrix"])
        candidate = np.asarray(result["candidate_matrix"])
        self.assertTrue(np.array_equal(candidate[:, 0], source[:, 0] * 1.5))
        self.assertTrue(np.array_equal(candidate[:, 1:], source[:, 1:]))
        self.assertEqual(
            result["matrix_digest"],
            "69528f0e204b51847c1d2a7df428555a557454e9fa6bc76768d39e7cc5a90da8",
        )

    def test_candidate_matrix_mutation_fails_closed(self):
        changed = copy.deepcopy(self.cfg)
        changed["candidate_requested_coordinate_matrix_columns"][0][0] += 1e-12
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            primary._validate_design(changed)
        with self.assertRaisesRegex(ValueError, "frozen-contract"):
            independent._validate_frozen_contract(changed)

    def test_candidate_selection_mutations_fail_closed(self):
        mutations = []
        changed = copy.deepcopy(self.cfg)
        changed["candidate_contract"]["fixed_scale"] = 1.49
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["candidate_contract"]["scaled_column_index"] = 1
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["candidate_contract"]["context_dependent_selection_allowed"] = True
        mutations.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["candidate_contract"]["search_allowed"] = True
        mutations.append(changed)
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    primary._validate_design(changed)
                with self.assertRaises(ValueError):
                    independent._validate_frozen_contract(changed)

    def test_safety_gate_mutations_fail_closed(self):
        for name, value in (
            ("maximum_incremental_normalized_action_linf", 0.251),
            ("maximum_ideal_return_incremental_linf", 0.241),
            ("maximum_current_utilization", 0.551),
            ("minimum_desired_applied_current_cosine", 0.979),
            ("maximum_relative_off_basis_residual", 0.101),
        ):
            changed = copy.deepcopy(self.cfg)
            changed["static_issue_contract"][name] = value
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    primary._validate_design(changed)
                with self.assertRaises(ValueError):
                    independent._validate_frozen_contract(changed)

    def test_timing_contract_mutations_fail_closed(self):
        for name, value in (
            ("normal_arrival_deadline_step", 26),
            ("normal_hold_through_step", 36),
            ("weak_arrival_deadline_step", 28),
            ("weak_hold_through_step", 38),
        ):
            changed = copy.deepcopy(self.cfg)
            changed["formal_timing_contract"][name] = value
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    primary._validate_design(changed)
                with self.assertRaises(ValueError):
                    independent._validate_frozen_contract(changed)

    def test_zero_tsc_and_no_rl_boundary(self):
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertEqual(execution["plant_steps_executed"], 0)
        self.assertFalse(execution["controller_executed"])
        self.assertFalse(execution["ray_executed"])
        self.assertFalse(execution["gotsc_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])
        self.assertTrue(self.cfg["scientific_scope"]["pass_authorizes_real_sentinel_design_only"])

    def test_source_identity_and_hashes_are_exact(self):
        source = self.cfg["source_r4_contract"]
        self.assertEqual(source["package_checkpoint"], "f5b8348")
        self.assertEqual(source["raw_count"], 200)
        self.assertEqual(source["required_signal_pass_count"], 254)
        self.assertEqual(len(source["required_failed_experiment_ids"]), 2)
        self.assertEqual(self.cfg["source_r2_contract"]["raw_count"], 72)
        self.assertEqual(
            source["package_digest"],
            "c9c6fc870618ecbefe1bf9891a6f918927c2062753e2750596d2e73ec7ecf523",
        )

    def test_primary_reads_nested_package_fingerprint(self):
        source = inspect.getsource(primary._authenticate_source)
        self.assertIn('manifest.get("package_fingerprint", {}).get("digest")', source)
        self.assertNotIn('manifest.get("package_digest")', source)

    def test_geometry_signature_accepts_report_order_not_gate_changes(self):
        base = {
            "evaluated": True,
            "passed": False,
            "context_count": 8,
            "issue_task_steps": [10, 14, 18, 22],
            "branch_count": 64,
            "branch_direction_count": 256,
            "signal_pass_count": 254,
            "rank_pass_count": 64,
            "condition_pass_count": 64,
            "minimum_direction_peak_normalized_outputs5": 0.00429800000001368,
            "maximum_condition_number": 11.570074108693706,
            "branch_rows": [{"source": "a"}, {"source": "b"}],
            "issue_coordinate_and_field_symmetry": {
                "source_pair_count": 32,
                "new_pair_count": 96,
                "combined_pair_count": 128,
                "coordinate_exact_count": 128,
                "physical_field_exact_count": 128,
                "passed": True,
            },
        }
        reordered = copy.deepcopy(base)
        reordered["branch_rows"].reverse()
        reordered["branch_rows"][0]["first_response_state"] = 15
        self.assertNotEqual(base, reordered)
        self.assertEqual(primary._geometry_signature(base), primary._geometry_signature(reordered))
        self.assertEqual(independent._geometry_signature(base), independent._geometry_signature(reordered))
        self.assertTrue(independent._source_geometry_matches(reordered, base, reordered))
        changed = copy.deepcopy(reordered)
        changed["signal_pass_count"] = 255
        self.assertNotEqual(primary._geometry_signature(base), primary._geometry_signature(changed))
        self.assertFalse(independent._source_geometry_matches(reordered, changed, reordered))
        self.assertFalse(independent._source_geometry_matches(reordered, base, base))

    def test_independent_does_not_import_primary(self):
        source = inspect.getsource(independent)
        self.assertNotIn("r14r5_global_direction0_gain_preflight as", source)
        self.assertNotIn("from docs.codex.audit_tools.stage4_2r3c3t13s24d1r14r5_global", source)
        self.assertIn("stage4_2r3c3t13s24d1r14r4_independent_forensics", source)

    def test_independent_strict_json_rejects_invalid_input(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            independent._loads('{"x": 1, "x": 2}')
        with self.assertRaisesRegex(ValueError, "nonstandard JSON constant"):
            independent._loads('{"x": NaN}')

    def test_launchers_force_server_venv_and_forbid_real_execution(self):
        shell = (ROOT / "scripts/stage4_2r3c3t13s24d1r14r5_shell_common.sh").read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r5_common.sh").read_text(encoding="utf-8")
        offline = (ROOT / "run_stage4_2r3c3t13s24d1r14r5_offline.sh").read_text(encoding="utf-8")
        verify = (ROOT / "run_stage4_2r3c3t13s24d1r14r5_verify_package.sh").read_text(encoding="utf-8")
        expected_python = "/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python"
        self.assertIn(expected_python, shell)
        self.assertIn(expected_python, verify)
        self.assertIn("zero controller/plant/Ray/gotsc/TSC", common)
        self.assertIn('exec bash "${PROJECT_DIR}/run_stage4_2r3c3t13s24d1r14r5_common.sh"', offline)
        self.assertNotIn("ray start", common.lower())
        self.assertNotIn("--backend ray", common.lower())
        self.assertNotIn(" gotsc ", common.lower())


if __name__ == "__main__":
    unittest.main()
