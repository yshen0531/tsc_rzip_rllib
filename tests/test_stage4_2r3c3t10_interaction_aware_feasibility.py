from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t10_interaction_aware_feasibility.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t10_interaction_aware_feasibility", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T10 interaction-aware feasibility tool")
T10 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T10)


class _QuadraticEvaluator:
    policy = {"allowed_arrival_steps": [1]}
    horizon = 1

    @staticmethod
    def endpoint_margin(values: np.ndarray, endpoint: int):
        assert endpoint == 1
        margin = 0.05 - (
            (float(values[0, 0]) - 0.4) ** 2
            + (float(values[0, 1]) + 0.3) ** 2
        )
        return margin, {
            "endpoint_step": 1,
            "minimum_signed_margin": margin,
            "active_constraint": "synthetic_quadratic",
        }

    def best(self, values: np.ndarray):
        return self.endpoint_margin(values, 1)


class Stage42R3C3T10Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = (
            ROOT
            / "configs/stage4_2r3c3t10_interaction_aware_feasibility_v1.json"
        )
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_design_and_source_hashes(self) -> None:
        T10._validate_design(self.config)
        source = self.config["source_contract"]
        self.assertEqual(
            T10._sha256(
                ROOT
                / "docs/codex/audit_tools/stage4_2r3c3t1_six_basis_feasibility_diagnostic.py"
            ),
            source["frozen_formal_evaluator_sha256"],
        )
        self.assertEqual(
            T10._sha256(
                ROOT
                / "tsc_rzip_rllib/diagnostics/stage4_2r3c3t9_pc3_mixed_interaction_identification.py"
            ),
            source["t9_runtime_source_sha256"],
        )
        compact = (
            ROOT
            / "docs/codex/audits/stage4_2r3c3t9_pc3_mixed_interaction_identification_20260731_090005/server_compact"
        )
        if compact.is_dir():
            names = {
                "stage4_2r3c3t9_manifest.json": "t9_manifest_sha256",
                "stage4_2r3c3t9_state.json": "t9_state_sha256",
                "stage4_2r3c3t9_summary.json": "t9_summary_sha256",
                "results.json": "t9_results_sha256",
                "stage4_2r3c3t9_server_audit.json": "t9_server_audit_sha256",
            }
            for name, field in names.items():
                self.assertEqual(T10._sha256(compact / name), source[field])

    def test_design_matrix_is_fixed_full_rank_and_conditioned(self) -> None:
        matrix = T10._design_matrix(math.sqrt(2.0))
        self.assertEqual(matrix.shape, (6, 6))
        self.assertEqual(np.linalg.matrix_rank(matrix), 6)
        self.assertAlmostEqual(
            float(np.linalg.cond(matrix)), 2.9897369702272503, places=12
        )
        self.assertLessEqual(float(np.linalg.cond(matrix)), 3.0)

    def test_six_term_fit_reconstructs_all_measured_nodes(self) -> None:
        rng = np.random.default_rng(20260731)
        baseline = rng.normal(size=(8, 3))
        expected_terms = rng.normal(scale=0.01, size=(6, 8, 3))
        q = math.sqrt(2.0)
        nodes = [
            baseline
            + np.tensordot(
                T10._features(stress, pc3), expected_terms, axes=(0, 0)
            )
            for stress, pc3 in T10._design_nodes(q)
        ]
        actual_terms, audit = T10._fit_terms(baseline, nodes, q)
        self.assertTrue(np.allclose(actual_terms, expected_terms, atol=1e-13))
        self.assertEqual(audit["rank"], 6)
        self.assertLessEqual(audit["maximum_node_reconstruction_abs_error"], 1e-13)

    def test_optimizer_is_bounded_and_finds_fixed_grid_solution(self) -> None:
        baseline = np.zeros((2, 3), dtype=float)
        terms = np.zeros((6, 2, 3), dtype=float)
        terms[0, 0, 0] = 1.0
        terms[1, 0, 1] = 1.0
        row = T10._optimize_context(
            _QuadraticEvaluator(),
            baseline,
            terms,
            self.config["model_contract"],
        )
        self.assertTrue(row["passed"])
        self.assertTrue(all(-1.0 <= value <= 1.0 for value in row["best_coordinates"]))
        self.assertTrue(np.allclose(row["best_coordinates"], [0.4, -0.3], atol=1e-9))

    def test_passing_route_still_cannot_authorize_r3c4(self) -> None:
        scope = self.config["scientific_scope"]
        self.assertFalse(scope["r3c4_implementation_authorized"])
        self.assertFalse(scope["bc_dagger_or_rl_allowed"])
        design = (
            ROOT
            / "docs/codex/reports/STAGE4_2R3C3T10_INTERACTION_AWARE_FEASIBILITY_DESIGN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("does **not** authorize R3c4", design)
        self.assertIn("64 stress-only", design)
        self.assertIn("64 PC3-only", design)

    def test_launcher_is_offline_and_has_no_broad_kill(self) -> None:
        texts = [
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "run_stage4_2r3c3t10_common.sh",
                "run_stage4_2r3c3t10_offline.sh",
                "run_stage4_2r3c3t10_nohup.sh",
            )
        ]
        combined = "\n".join(texts)
        self.assertNotIn("gotsc", combined)
        self.assertNotIn("pkill", combined)
        self.assertNotIn("ray stop --force", combined)
        self.assertIn("read-only offline audit", combined)


if __name__ == "__main__":
    unittest.main()
