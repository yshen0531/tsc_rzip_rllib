from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs"
    / "codex"
    / "audit_tools"
    / "stage4_2r3c3t2_six_basis_feasibility_audit.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t2_six_basis_feasibility_audit", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T2 six-basis feasibility audit")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class Stage42R3C3T2SixBasisAuditTests(unittest.TestCase):
    def test_frozen_corrected_feasibility_tool_is_exact(self) -> None:
        tool = (
            ROOT
            / "docs"
            / "codex"
            / "audit_tools"
            / "stage4_2r3c3t1_six_basis_feasibility_diagnostic.py"
        )
        loaded = AUDIT._load_frozen_tool(tool)
        self.assertTrue(callable(loaded._velocity_condition))
        self.assertTrue(callable(loaded._optimize_context))

    def test_numeric_audit_and_controller_keys_match_without_labels(
        self,
    ) -> None:
        visible = [0.7, 0.01, 30000.0, *[float(i) for i in range(14)]]
        audit = {
            "initial_visible": visible,
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.01,
            "target_Ip_offset_A": 0.0,
            "actual_delay_steps": 2,
            "actuator_gain_by_mode": [1.0, 0.9, 1.0],
            "actual_slew_scale": 0.9,
        }
        controller = {
            "initial_R_m": visible[0],
            "initial_Z_m": visible[1],
            "initial_Ip_A": visible[2],
            "initial_coil_currents_A": visible[3:],
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.01,
            "target_Ip_offset_A": 0.0,
            "actuator_delay_steps": 2,
            "actuator_gain_by_mode": [1.0, 0.9, 1.0],
            "actuator_slew_scale": 0.9,
        }
        self.assertEqual(
            AUDIT._numeric_audit_key(audit),
            AUDIT._numeric_controller_key(controller),
        )

    def test_signed_response_preserves_tail_and_uses_formal_prefix(
        self,
    ) -> None:
        def result(sign: int) -> dict:
            schedule = {}
            for state in [3, 4, 5, 6, 7, 8]:
                schedule[str(state - 1)] = [0.006 * sign, 0.0, 0.0]
            for state in [39, 40, 41, 42, 43, 44]:
                schedule[str(state - 1)] = [-0.006 * sign, 0.0, 0.0]
            return {
                "spec": {
                    "r3c3_probe_id": "held_transport_mode0",
                    "r3c3_probe_mode": 0,
                    "r3c3_probe_sign": sign,
                    "r3c3_probe_amplitude": 0.006,
                    "formal_horizon_steps": 35,
                    "r3c3_probe_delta_by_task_issue_step": schedule,
                }
            }

        plus_y = np.arange(153, dtype=float).reshape(51, 3)
        minus_y = -plus_y
        plus_v = np.arange(102, dtype=float).reshape(51, 2)
        minus_v = -plus_v
        with mock.patch.object(
            AUDIT.t2,
            "_arrays",
            side_effect=[
                (plus_y, plus_v),
                (minus_y, minus_v),
            ],
        ):
            audit, controller, formal_y, formal_v = AUDIT._signed_response(
                plus=result(1),
                minus=result(-1),
                plus_path=SCRIPT,
                minus_path=SCRIPT,
                horizon=35,
                basis_index=4,
            )
        self.assertEqual(formal_y.shape, (36, 3))
        self.assertEqual(formal_v.shape, (36, 2))
        self.assertEqual(len(audit["full_delta_RZI_by_state"]), 51)
        self.assertEqual(len(controller["delta_RZI_by_state"]), 36)
        self.assertNotIn("plus_file", controller)
        self.assertNotIn("audit_probe_id", controller)
        self.assertEqual(controller["basis_index"], 4)


if __name__ == "__main__":
    unittest.main()
