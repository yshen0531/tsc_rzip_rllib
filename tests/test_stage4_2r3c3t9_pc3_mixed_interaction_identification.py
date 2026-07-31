from __future__ import annotations

import copy
import json
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np


runpy.run_path(str(Path(__file__).resolve().parent / "conftest.py"))

from tsc_rzip_rllib.diagnostics import (  # noqa: E402
    stage4_2r3c3t9_pc3_mixed_interaction_identification as t9,
)
from scripts import stage4_2r3c3t9_server_postprocess as postprocess  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs"
    / "stage4_2r3c3t9_pc3_mixed_interaction_identification_500ms.json"
)


class Stage42R3C3T9IdentificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_self_test_and_frozen_config(self) -> None:
        t9._validate_config(self.cfg)
        result = t9.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(result["expected_rollouts"], 224)
        self.assertFalse(result["real_tsc_executed"])

    def test_all_frozen_schedules_are_delay_aware_and_zero_net(self) -> None:
        _, preflight = t9._authenticate_preflight(self.cfg)
        for case in preflight["actuator_cases"]:
            delay = int(case["delay_steps"])
            hold = int(case["formal_hold_step"])
            schedules = [
                case["standalone_pc3_probe"],
                *case["mixed_factorial"]["probes"],
            ]
            for frozen in schedules:
                schedule = t9._schedule(frozen)
                effects = sorted(step + delay + 1 for step in schedule)
                self.assertEqual(len(schedule), 41)
                self.assertEqual(
                    effects[:35], list(range(delay + 1, hold + 1))
                )
                self.assertEqual(effects[35:], [39, 40, 41, 42, 43, 44])
                net = np.sum(np.stack(list(schedule.values())), axis=0)
                self.assertLess(float(np.max(np.abs(net))), 1.0e-12)
                self.assertLessEqual(
                    max(
                        float(np.max(np.abs(value)))
                        for value in schedule.values()
                    ),
                    0.0075,
                )

    def test_build_specs_has_exact_independent_224_identity_matrix(self) -> None:
        templates = []
        for pair in range(4):
            for history in ("plus_first", "minus_first"):
                for target in ("nominal", "RZ_p10_m10"):
                    for delay, slew in ((0, 1.0), (2, 0.9)):
                        templates.append(
                            {
                                "pair_id": f"pair_{pair}",
                                "history_member": history,
                                "target_id": target,
                                "action_delay_steps": delay,
                                "slew_scale": slew,
                                "baseline_experiment_id": (
                                    f"base_{pair}_{history}_{target}_{delay}"
                                ),
                            }
                        )
        preflight_path, preflight = t9._authenticate_preflight(self.cfg)
        ctx = t9.Stage42R3C3T9Context(
            cfg=copy.deepcopy(self.cfg),
            base_config_path=ROOT / self.cfg["base_stage_config"],
            base_ctx=SimpleNamespace(
                source_ctx=object(),
                source_t1_fingerprint={"raw_inventory_digest": "digest"},
            ),
            preflight_path=preflight_path,
            preflight=preflight,
            t7_controller_bank_path=Path("bank.json"),
            paths=t9._paths(ROOT / ".codex_tmp" / "unused_t9_test"),
        )
        with mock.patch.object(
            t9.t1, "build_control_specs", return_value=templates
        ):
            specs = t9.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 224)
        self.assertEqual(len({item["experiment_id"] for item in specs}), 224)
        self.assertEqual(
            sum(
                item["r3c3_probe_id"] == t9.BASELINE_PROBE_ID
                for item in specs
            ),
            32,
        )
        self.assertEqual(
            sum(
                item["r3c3t9_probe_family"] == "standalone_pc3"
                for item in specs
            ),
            64,
        )
        self.assertEqual(
            sum(
                item["r3c3t9_probe_family"] == "mixed_factorial"
                for item in specs
            ),
            128,
        )
        self.assertTrue(
            all(
                not item["pair_or_history_label_available_to_controller"]
                for item in specs
            )
        )
        self.assertTrue(
            all(
                not item["hidden_wire_current_available_to_controller"]
                for item in specs
            )
        )

    def test_walsh_contrast_recovers_exact_mixed_term(self) -> None:
        baseline = np.asarray([10.0, -5.0])
        stress = np.asarray([2.0, 3.0])
        pc3 = np.asarray([-4.0, 1.0])
        mixed = np.asarray([0.25, -0.75])
        arrays = {
            (stress_sign, pc3_sign): (
                baseline
                + stress_sign * stress
                + pc3_sign * pc3
                + stress_sign * pc3_sign * mixed
            )
            for stress_sign, pc3_sign in t9.FACTORIAL_SIGNS
        }
        actual = t9._walsh_contrasts(arrays)
        for expected, value in zip(
            (baseline, stress, pc3, mixed), actual
        ):
            np.testing.assert_array_equal(value, expected)

    def test_linear_route_is_separate_from_identification(self) -> None:
        numerator = np.asarray([1.0, 0.0])
        self.assertAlmostEqual(t9._norm_ratio(numerator, 10.0), 0.1)
        self.assertTrue(
            t9._norm_ratio(numerator, 10.0)
            <= self.cfg["identification_probe"][
                "maximum_mixed_velocity_norm_ratio_for_linear_route"
            ]
        )
        self.assertGreater(t9._norm_ratio(numerator, 5.0), 0.1)

    def test_postprocess_preserves_separate_route_classification(self) -> None:
        fields = postprocess._summary_fields(
            {
                "identification_passed": True,
                "linear_route_passed": False,
                "passed": True,
            }
        )
        self.assertTrue(fields["identification_passed"])
        self.assertFalse(fields["linear_route_passed"])
        self.assertTrue(fields["passed"])


if __name__ == "__main__":
    unittest.main()
