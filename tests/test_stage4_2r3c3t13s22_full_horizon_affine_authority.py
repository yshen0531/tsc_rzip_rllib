from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t13s22_full_horizon_affine_authority.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t13s22_full_horizon_affine_authority", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T13S22 affine authority discriminator")
S22 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S22
SPEC.loader.exec_module(S22)


def _trajectory(rzi: np.ndarray, experiment_id: str) -> dict:
    rows = []
    for index, values in enumerate(np.asarray(rzi, dtype=float)):
        rows.append(
            {
                "R": float(values[0]),
                "Z": float(values[1]),
                "Ip": float(values[2]),
                "action_norm_tsc": [0.0] * 14,
                "currents_a_display": [0.0] * 14,
            }
        )
    return {
        "experiment_id": experiment_id,
        "success": True,
        "failure_reason": "",
        "trajectory": rows,
    }


class Stage42R3C3T13S22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = (
            ROOT
            / "configs/stage4_2r3c3t13s22_full_horizon_affine_authority_v1.json"
        )
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_design_validates_and_blocks_scope_expansion(self) -> None:
        S22._validate_design(self.config)
        response = self.config["response_contract"]
        execution = self.config["execution_contract"]
        scope = self.config["scientific_scope"]
        self.assertFalse(response["allow_direction_rescaling"])
        self.assertFalse(response["allow_new_basis"])
        self.assertFalse(response["allow_per_step_coefficients"])
        self.assertFalse(execution["ray_executed"])
        self.assertFalse(execution["gotsc_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertFalse(execution["controller_executed"])
        self.assertFalse(scope["bc_dagger_or_rl_allowed"])

    def test_design_change_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["optimizer_contract"]["seed"] += 1
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            S22._validate_design(changed)

    def test_odd_and_even_response_construction(self) -> None:
        n = 15
        baseline_rzi = np.column_stack(
            (
                np.linspace(1.0, 1.01, n),
                np.linspace(-0.2, -0.19, n),
                np.linspace(500000.0, 500100.0, n),
            )
        )
        baseline = _trajectory(baseline_rzi, "baseline")
        probes = {}
        for index, direction in enumerate(S22.DIRECTIONS):
            odd = np.zeros_like(baseline_rzi)
            even = np.zeros_like(baseline_rzi)
            odd[11:, 0] = (index + 1) * np.arange(1, n - 10) * 1e-4
            odd[11:, 1] = -(index + 1) * 2e-4
            odd[11:, 2] = (index + 1) * 10.0
            even[11:, 0] = 1e-5
            plus = _trajectory(
                baseline_rzi + odd + even, f"{direction}_plus"
            )
            minus = _trajectory(
                baseline_rzi - odd + even, f"{direction}_minus"
            )
            probes[(direction, 1)] = plus
            probes[(direction, -1)] = minus
        built = S22._construct_responses(
            baseline, probes, effect_start=11, dt_s=0.01
        )
        self.assertEqual(built["odd_rzi"].shape, (4, n, 3))
        self.assertTrue(np.all(built["odd_rzi"][:, :11] == 0.0))
        self.assertTrue(np.allclose(built["odd_rzi"][3, 11:, 0], odd[11:, 0]))
        self.assertTrue(
            np.allclose(built["even_outputs5"][:, 11:, 0], 1e-5)
        )
        self.assertTrue(np.all(np.isfinite(built["even_outputs5"])))

    def test_synthetic_result_changes_only_rzi(self) -> None:
        source = _trajectory(np.ones((4, 3)), "base")
        source["trajectory"][0]["preserved"] = "yes"
        replacement = np.arange(12, dtype=float).reshape(4, 3)
        result = S22._synthetic_result(source, replacement)
        self.assertEqual(result["trajectory"][0]["preserved"], "yes")
        self.assertEqual(result["trajectory"][3]["Ip"], 11.0)
        self.assertEqual(source["trajectory"][3]["Ip"], 1.0)

    def test_primary_route_requires_every_context(self) -> None:
        reproduction = {
            "baseline_formal_reproduction_count": 40,
            "measured_probe_formal_reproduction_count": 320,
        }
        primary = {
            "finite_direction_construction": 40,
            "optimizer_completion": 40,
            "independent_check": 40,
            "optimistic_affine_formal_feasibility": 40,
        }
        passed, route = S22._route_from_counts(
            360, reproduction, primary, self.config
        )
        self.assertTrue(passed)
        self.assertEqual(route, self.config["routes"]["pass"])
        primary["optimistic_affine_formal_feasibility"] = 39
        passed, route = S22._route_from_counts(
            360, reproduction, primary, self.config
        )
        self.assertFalse(passed)
        self.assertEqual(route, self.config["routes"]["fail"])

    def test_launchers_are_stage_specific_and_zero_tsc(self) -> None:
        texts = [
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "run_stage4_2r3c3t13s22_common.sh",
                "run_stage4_2r3c3t13s22_offline.sh",
                "run_stage4_2r3c3t13s22_nohup.sh",
                "scripts/stage4_2r3c3t13s22_shell_common.sh",
            )
        ]
        combined = "\n".join(texts)
        self.assertNotIn("pkill", combined)
        self.assertNotIn("ray stop", combined)
        self.assertNotIn("--resume", combined)
        self.assertNotIn("gotsc", combined.lower())
        self.assertIn("read-only S21 raw", combined)
        self.assertIn("stage4_2r3c3t13s22", combined)

    def test_design_document_preserves_claim_boundary(self) -> None:
        design = (
            ROOT
            / "docs/codex/reports/STAGE4_2R3C3T13S22_FULL_HORIZON_AFFINE_AUTHORITY_DESIGN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("does not assume that an affine combination is physically realizable", design)
        self.assertIn("authorize a real MPC", design)
        self.assertIn("BC, DAgger, and bounded residual RL remain prohibited", design)


if __name__ == "__main__":
    unittest.main()
