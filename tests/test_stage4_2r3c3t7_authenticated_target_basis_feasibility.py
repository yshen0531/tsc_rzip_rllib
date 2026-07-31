from __future__ import annotations

import importlib.util
import json
import runpy
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "tests" / "conftest.py"))
SCRIPT = (
    ROOT
    / "docs"
    / "codex"
    / "audit_tools"
    / "stage4_2r3c3t7_authenticated_target_basis_feasibility.py"
)
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t7_authenticated_target_basis_feasibility_v1.json"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t7_authenticated_target_basis_feasibility", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T7 audit")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class Stage42R3C3T7Tests(unittest.TestCase):
    def test_frozen_design_is_exact(self) -> None:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        AUDIT._validate_design(cfg)
        self.assertEqual(
            cfg["selected_t3_basis_indices"], [0, 1, 2, 3, 7]
        )
        self.assertEqual(
            cfg["selected_t6_probe_ids"],
            list(AUDIT.t6.PROBE_IDS),
        )
        self.assertFalse(
            cfg["selection_policy"]["posthoc_column_scaling_allowed"]
        )

    def test_global_selector_is_deterministic_and_not_label_conditioned(
        self,
    ) -> None:
        matrices = []
        for scale in (1.0, 1.1, 1.2):
            matrix = np.zeros((16, 11), dtype=float)
            matrix[:11, :] = np.eye(11) * scale
            matrix[:, 8] += matrix[:, 4] * 0.5
            matrix[:, 9] += matrix[:, 5] * 0.5
            matrix[:, 10] += matrix[:, 6] * 0.5
            matrices.append(matrix)
        selected = AUDIT._select_global_subset(
            matrices, size=8, maximum=25.0
        )
        self.assertEqual(selected["pass_count"], 3)
        self.assertEqual(len(selected["indices"]), 8)
        self.assertEqual(selected["minimum_rank"], 8)

    def test_signed_response_rejects_non_opposite_schedule(self) -> None:
        schedule = {str(index): [0.001, 0.0, 0.0] for index in range(41)}
        plus = {
            "spec": {
                "r3c3_probe_id": AUDIT.t6.PROBE_IDS[0],
                "r3c3_probe_sign": 1,
                "r3c3_probe_delta_by_task_issue_step": schedule,
                "r3c3_probe_amplitude": 0.001,
                "r3c3_probe_first_effect_state": 1,
            }
        }
        minus = {
            "spec": {
                **plus["spec"],
                "r3c3_probe_sign": -1,
            }
        }
        with self.assertRaises(ValueError):
            AUDIT._response_from_signed_pair(
                plus,
                minus,
                SCRIPT,
                SCRIPT,
                probe_id=AUDIT.t6.PROBE_IDS[0],
                basis_index=5,
                horizon=35,
            )


if __name__ == "__main__":
    unittest.main()
