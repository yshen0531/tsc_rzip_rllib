from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s10_combined_postqueue_first_effect_audit as audit,
)


class Stage42R3C3T13S10CombinedPostqueueFirstEffectAuditTests(unittest.TestCase):
    def test_exact_file_authentication_rejects_wrong_hash(self) -> None:
        with mock.patch.object(audit.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "design SHA-256"):
                audit.authenticate_exact_file(
                    Path("design.md"), audit.DESIGN_SHA256, "design"
                )

    def test_q1_trace_adapter_is_in_memory_and_event_only(self) -> None:
        raw = [
            {
                "controller_trace": [
                    {"r3c3t13s9_lattice_event": "issue", "unchanged": 7},
                    {"r3c3t13s9_lattice_event": "cancel", "unchanged": 8},
                ],
                "spec": {"identity": "source"},
            }
        ]
        adapted = audit.adapt_q1_trace_contract(raw)
        self.assertNotIn("r3c3t13s5_lattice_event", raw[0]["controller_trace"][0])
        self.assertEqual(
            [row["r3c3t13s5_lattice_event"] for row in adapted[0]["controller_trace"]],
            ["issue", "cancel"],
        )
        self.assertIs(adapted[0]["spec"], raw[0]["spec"])
        self.assertEqual(adapted[0]["controller_trace"][0]["unchanged"], 7)

    def test_q1_trace_adapter_rejects_unknown_event(self) -> None:
        raw = [{"controller_trace": [{"r3c3t13s9_lattice_event": "future"}]}]
        with self.assertRaisesRegex(ValueError, "invalid q1 lattice event"):
            audit.adapt_q1_trace_contract(raw)

    def test_nonschedule_probe_contract_ignores_only_schedule(self) -> None:
        left = {"lattice_probe": {"rank": 4, "schedule_by_delay": {"2": "late"}}}
        right = {"lattice_probe": {"rank": 4, "schedule_by_delay": {"2": "now"}}}
        self.assertEqual(
            audit._probe_contract_without_schedule(left),
            audit._probe_contract_without_schedule(right),
        )
        right["lattice_probe"]["rank"] = 3
        self.assertNotEqual(
            audit._probe_contract_without_schedule(left),
            audit._probe_contract_without_schedule(right),
        )

    def test_fit_model_enforces_rank_condition_signal_and_tube(self) -> None:
        samples = []
        for index in range(4):
            x = np.zeros(14)
            x[index] = 1.0
            y = np.zeros(5)
            y[index % 5] = 1e-3
            samples.append(
                {
                    "odd_input": x,
                    "odd_output": y,
                    "signed": {
                        -1: {"input": -x, "output": -y},
                        1: {"input": x, "output": y},
                    },
                }
            )
        context = {
            "context_id": "context_00",
            "campaign": "q1_t13s9",
            "stratum": "easy",
            "samples": {"transport": samples},
        }
        cfg = {
            "tube_caps_unscaled": [1.0] * 5,
            "tube_residual_multiplier": 1.5,
            "response_scales": [0.03, 0.03, 0.1, 0.1, 2000.0],
            "signal_floor_multiplier": 1.0,
            "maximum_development_condition_number": 15.0,
        }
        model = audit._fit_model(context, "transport", cfg)
        self.assertTrue(model["signal_pass"])
        self.assertTrue(model["rank_condition_pass"])
        self.assertTrue(model["tube_pass"])
        self.assertAlmostEqual(model["condition_number"], 1.0)

    def test_routes_preserve_controller_and_rl_block(self) -> None:
        self.assertIn("Q3_HOLDOUT_REQUIRED", audit.PASS_ROUTE)
        self.assertIn("OBSERVER_REDESIGN", audit.FAIL_ROUTE)
        self.assertNotEqual(audit.PASS_ROUTE, audit.FAIL_ROUTE)


if __name__ == "__main__":
    unittest.main()
