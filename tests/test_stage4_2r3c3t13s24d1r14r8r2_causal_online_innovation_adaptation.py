from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

from tsc_rzip_rllib.control import causal_online_innovation_adapter as adapter
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation as r8r2,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R2_CAUSAL_ONLINE_INNOVATION_ADAPTATION_DESIGN.md"
PRIMARY = ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation.py"
INDEPENDENT = ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r2_independent_forensics.py"
RUNNER = ROOT / "scripts/run_stage4_2r3c3t13s24d1r14r8r2_causal_online_innovation_adaptation.sh"


def _visible(cfg: dict, count: int = 40) -> np.ndarray:
    value = np.zeros((count, 5), dtype=float)
    step = np.arange(count, dtype=float)
    value[:, 2] = 0.12 + 0.002 * step
    value[:, 3] = -0.08 + 0.001 * step
    value[:, 4] = 0.25 - 0.0005 * step
    value[0, :2] = (1.0, -0.5)
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    dt = float(cfg["bank_contract"]["dt_s"])
    for index in range(1, count):
        value[index, 0] = value[index - 1, 0] + value[index, 2] * dt * scales[2] / scales[0]
        value[index, 1] = value[index - 1, 1] + value[index, 3] * dt * scales[3] / scales[1]
    return value


class Stage42R8R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_design_and_self_test(self):
        r8r2.validate_config(self.cfg)
        self.assertEqual(
            hashlib.sha256(DESIGN.read_bytes()).hexdigest(),
            self.cfg["design_document_sha256"],
        )
        self.assertTrue(r8r2.self_test(CONFIG)["passed"])
        self.assertEqual(adapter.fixed_candidate(self.cfg).as_dict(), self.cfg["fixed_candidate"])
        self.assertEqual(self.cfg["new_tsc_rollouts"], 0)
        self.assertFalse(self.cfg["gate_a_qualified"])

    def test_no_action_forecast_and_descriptor_are_causal(self):
        visible = _visible(self.cfg)
        forecast = adapter.no_action_forecast(visible, 10, self.cfg)
        descriptor = adapter.probe_descriptor(visible, 10, (0.01, -0.02, 500.0), self.cfg)
        changed = visible.copy()
        changed[11:] += 1000.0
        np.testing.assert_array_equal(
            adapter.no_action_forecast(changed, 10, self.cfg), forecast
        )
        np.testing.assert_array_equal(
            adapter.probe_descriptor(changed, 10, (0.01, -0.02, 500.0), self.cfg),
            descriptor,
        )

    def test_online_adapter_ignores_future_and_matched_baseline(self):
        issue, update, count = 10, 2, 20
        baseline = _visible(self.cfg)
        response = np.zeros((count, 5), dtype=float)
        response[:, 2] = 0.06
        response[:, 3] = -0.03
        response[:, 4] = 0.01
        scales = np.asarray(self.cfg["bank_contract"]["response_scales"], dtype=float)
        dt = float(self.cfg["bank_contract"]["dt_s"])
        response[:, 0] = np.cumsum(response[:, 2]) * dt * scales[2] / scales[0]
        response[:, 1] = np.cumsum(response[:, 3]) * dt * scales[3] / scales[1]
        probe = baseline.copy()
        probe[issue + 1 : issue + 1 + count] += response
        cold = response.copy()
        cold[:, 2:5] *= 0.5
        cold[:, 0] = np.cumsum(cold[:, 2]) * dt * scales[2] / scales[0]
        cold[:, 1] = np.cumsum(cold[:, 3]) * dt * scales[3] / scales[1]
        item = {
            "issue_task_step": issue,
            "probe_visible": probe,
            "baseline_visible": baseline,
            "response": response,
        }
        expected = adapter.adapted_prediction(item, cold, update, 0.5, self.cfg)
        changed = copy.deepcopy(item)
        changed["probe_visible"] = probe.copy()
        changed["probe_visible"][issue + update + 1 :] += 999.0
        changed["baseline_visible"] = baseline + 777.0
        changed["response"] = response + 555.0
        np.testing.assert_array_equal(
            adapter.adapted_prediction(changed, cold, update, 0.5, self.cfg),
            expected,
        )
        self.assertEqual(expected.shape, (8, 5))

    def test_baseline_gate_covers_all_96_windows_and_fails_closed(self):
        visible = _visible(self.cfg)
        windows = []
        for context in range(24):
            for issue in (10, 14, 18, 22):
                windows.append(
                    {
                        "context_id": f"context_{context:02d}",
                        "pair_id": f"pair_{context // 2:02d}",
                        "history_member": f"history_{context % 2}",
                        "issue_task_step": issue,
                        "baseline_visible": visible,
                    }
                )
        passed = adapter.baseline_forecast_audit(windows, self.cfg)
        self.assertTrue(passed["passed"])
        self.assertEqual((passed["window_count"], passed["pass_count"]), (96, 96))
        failed = copy.deepcopy(windows)
        failed[0]["baseline_visible"] = visible.copy()
        failed[0]["baseline_visible"][11, 0] += 0.2
        outcome = adapter.baseline_forecast_audit(failed, self.cfg)
        self.assertFalse(outcome["passed"])
        self.assertEqual(outcome["pass_count"], 95)

    def test_update_selection_and_routes_are_fail_closed(self):
        self.assertEqual(
            adapter.select_update({2: {"passed": False}, 4: {"passed": True}}, self.cfg),
            4,
        )
        self.assertEqual(
            adapter.select_update({2: {"passed": True}, 4: {"passed": True}}, self.cfg),
            2,
        )
        self.assertEqual(
            r8r2.route_for(False, None, self.cfg), self.cfg["routes"]["baseline_fail"]
        )
        self.assertEqual(
            r8r2.route_for(True, None, self.cfg), self.cfg["routes"]["adaptation_fail"]
        )
        self.assertEqual(r8r2.route_for(True, 2, self.cfg), self.cfg["routes"]["pass"])

    def test_contract_mutations_fail(self):
        mutations = []
        changed = copy.deepcopy(self.cfg); changed["innovation_contract"]["update_relative_lags"] = [1, 2]; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["innovation_contract"]["matched_baseline_predictor_input_allowed"] = True; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["gates"]["useful_required_response_pass_count"] = 800; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["formal_timing_contract"]["normal_arrival_deadline_step"] = 26; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["new_tsc_rollouts"] = 1; mutations.append(changed)
        changed = copy.deepcopy(self.cfg); changed["gate_a_qualified"] = True; mutations.append(changed)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    r8r2.validate_config(value)

    def test_independent_path_is_structurally_separate(self):
        source = INDEPENDENT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        self.assertIn("stage4_2r3c3t13s24d1r14r7r2_independent_forensics", imported)
        self.assertNotIn("causal_online_innovation_adapter", imported)
        self.assertNotIn("from scripts import", source)
        self.assertIn("def _forecast", source)
        self.assertIn("def _adapt", source)

    def test_primary_and_independent_are_zero_tsc(self):
        for path in (PRIMARY, INDEPENDENT):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("import ray", source)
            self.assertNotIn("gotsc(", source)
            self.assertNotIn("plant.step", source)
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("ray start", runner)
        self.assertFalse(self.cfg["probe_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["mpc_validated"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
