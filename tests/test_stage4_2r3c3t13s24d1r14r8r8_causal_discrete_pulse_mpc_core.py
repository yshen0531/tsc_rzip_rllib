from __future__ import annotations

import copy
import json
import math
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r8_independent_forensics as independent,
)
from tsc_rzip_rllib.control import causal_discrete_pulse_mpc as mpc
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_campaign as campaign,
    stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_mpc_core as contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT
    / "configs/stage4_2r3c3t13s24d1r14r8r8_causal_discrete_pulse_receding_horizon_mpc_core_370ms.json"
)


class CausalDiscretePulseMPCCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_contract_and_self_test(self) -> None:
        contract.validate_config(self.cfg, project_root=ROOT)
        result = contract.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["decision_count"], 4)
        self.assertEqual(result["candidate_count"], 9)
        self.assertEqual(result["nonzero_candidate_count"], 8)
        self.assertFalse(self.cfg["all_stage_trajectories_allowed_in_expert_dataset"])
        self.assertFalse(self.cfg["gate_a_qualified"])
        self.assertFalse(self.cfg["bc_dagger_or_rl_allowed"])

    def test_contract_rejects_candidate_objective_and_safety_mutation(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["candidate_contract"]["ordered_candidates"][1]["action_scale"] = 0.9
        with self.assertRaisesRegex(ValueError, "candidate"):
            contract.validate_config(changed)
        changed = copy.deepcopy(self.cfg)
        changed["objective_contract"]["required_nonzero_score_ratio"] = 1.0
        with self.assertRaisesRegex(ValueError, "objective"):
            contract.validate_config(changed)
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["maximum_online_cancel_incremental_linf"] = 0.25
        with self.assertRaisesRegex(ValueError, "controller"):
            contract.validate_config(changed)

    def test_robust_objective_matches_hand_calculation(self) -> None:
        prediction = np.arange(20, dtype=float).reshape(4, 5) / 10.0
        tube = np.full((4, 5), 0.05)
        desired = np.asarray([0.2, -0.1, 0.0, 0.1, 1.0])
        objective = {
            "physical_scales": [1.0, 2.0, 3.0, 4.0, 5.0],
            "component_weights": [1.0, 2.0, 3.0, 4.0, 5.0],
            "lag_weights": [1.0, 2.0, 4.0, 8.0],
        }
        score, upper = mpc.robust_score(prediction, tube, desired, objective)
        scales = np.asarray(objective["physical_scales"])
        expected_upper = np.abs(prediction * scales - desired) + tube
        expected_score = np.sum(
            np.asarray(objective["lag_weights"])[:, None]
            * np.asarray(objective["component_weights"])[None, :]
            * np.square(expected_upper / scales)
        )
        np.testing.assert_array_equal(upper, expected_upper)
        self.assertEqual(score, float(expected_score))

    def _forecasts(self, first_score: float) -> list[dict[str, object]]:
        rows = []
        for order, candidate in enumerate(mpc.candidates(self.cfg)):
            rows.append(
                {
                    "order": order,
                    "name": candidate.name,
                    "direction_index": candidate.direction_index,
                    "sign": candidate.sign,
                    "score": 100.0 if order == 0 else first_score + order - 1,
                }
            )
        return rows

    def test_selector_threshold_tie_order_and_nonfinite_fail_closed(self) -> None:
        result = mpc.select_candidate(
            self._forecasts(99.5),
            ["direction0_plus", "direction0_minus"],
            0.995,
        )
        self.assertEqual(result["selected_name"], "direction0_minus")
        result = mpc.select_candidate(
            self._forecasts(99.5000000001), ["direction0_minus"], 0.995
        )
        self.assertEqual(result["selected_name"], "zero")
        rows = self._forecasts(99.0)
        rows[1]["score"] = math.nan
        with self.assertRaisesRegex(ValueError, "non-finite"):
            mpc.select_candidate(rows, ["direction0_minus"], 0.995)
        with self.assertRaisesRegex(ValueError, "unknown"):
            mpc.select_candidate(self._forecasts(99.0), ["unfrozen"], 0.995)

    def test_visible_history_and_descriptor_ignore_unavailable_future(self) -> None:
        states = [
            {"R": 0.7 + index * 0.001, "Z": -0.02 + index * 0.002, "Ip": 29000 + index}
            for index in range(30)
        ]
        scales = self.cfg["objective_contract"]["physical_scales"]
        prefix = mpc.visible_history(states[:23], scales)
        changed = copy.deepcopy(states)
        for row in changed[23:]:
            row.update({"R": 1e6, "Z": -1e6, "Ip": 1e12})
        np.testing.assert_array_equal(prefix, mpc.visible_history(changed[:23], scales))
        source_cfg = json.loads((ROOT / self.cfg["source_r8r7_config"]).read_text(encoding="utf-8"))
        full_visible = mpc.visible_history(states, scales)
        original = mpc.response_descriptor(full_visible, [0.01, -0.02, 5000.0], 22, source_cfg)
        full_visible[23:] += 1e9
        np.testing.assert_array_equal(
            original,
            mpc.response_descriptor(full_visible, [0.01, -0.02, 5000.0], 22, source_cfg),
        )

    def test_issue_and_cancel_construction_are_pure_and_exact(self) -> None:
        center_fields = tuple(["0.00000000"] * 14)
        target_fields = tuple(["1.00000000"] + ["0.00000000"] * 13)

        class FakeActuator:
            turns_tsc = tuple([1000.0] * 14)
            max_slew_step_a = 1000.0
            minimum_current_a_tsc = tuple([-1e6] * 14)
            maximum_current_a_tsc = tuple([1e6] * 14)

            def apply(self, _currents: object, action: object) -> SimpleNamespace:
                values = np.asarray(action, dtype=float)
                fields = target_fields if values[0] > 0.0 else center_fields
                return SimpleNamespace(
                    card15_fields=fields,
                    action_saturated=tuple([False] * 14),
                    current_limit_clipped=tuple([False] * 14),
                    nominal_readback_current_a_tsc=tuple(values),
                )

        calls = [
            {
                "action_norm_tsc": [0.1] + [0.0] * 13,
                "incremental_normalized_action_linf": 0.1,
                "total_normalized_action_abs": 0.1,
                "predicted_maximum_current_utilization": 0.1,
                "passed": True,
            },
            {
                "action_norm_tsc": [-0.1] + [0.0] * 13,
                "incremental_normalized_action_linf": 0.1,
                "total_normalized_action_abs": 0.1,
                "predicted_maximum_current_utilization": 0.1,
                "passed": True,
            },
        ]
        basis = np.zeros((4, 14), dtype=float)
        basis[:, :4] = np.eye(4)
        currents = [0.0] * 14
        currents_before = copy.deepcopy(currents)
        basis_before = basis.copy()

        def exact_target(_center: object, delta: object, **_kwargs: object) -> tuple[object, ...]:
            values = tuple(delta)
            return target_fields, tuple(Decimal(str(value)) for value in values), tuple([0] * 14)

        with mock.patch.object(mpc.s21, "_dynamic_exact_target", side_effect=exact_target), mock.patch.object(
            mpc.s9, "exact_stored_center_action", side_effect=calls
        ):
            issue = mpc.construct_issue(
                task_step=10,
                currents_a_tsc=currents,
                fixed_basis_delta_field_kat_tsc=basis,
                candidate=mpc.Candidate("direction0_plus", 0, 1, 1.0),
                canonical_matrix_columns=self.cfg["candidate_contract"]["canonical_matrix_columns"],
                actuator=FakeActuator(),
                controller_cfg=self.cfg["controller_contract"],
                lattice_cfg={},
            )
            cancel = mpc.construct_cancel(
                task_step=11,
                currents_a_tsc=issue["nominal_issue_readback_current_a_tsc"],
                issue_event=issue,
                actuator=FakeActuator(),
                controller_cfg=self.cfg["controller_contract"],
                lattice_cfg={},
            )
        self.assertTrue(issue["passed"], issue["criteria"])
        self.assertTrue(cancel["passed"], cancel["criteria"])
        self.assertEqual(cancel["stored_center_card15_fields"], list(center_fields))
        self.assertEqual(currents, currents_before)
        np.testing.assert_array_equal(basis, basis_before)

    def test_runtime_model_exception_uses_zero_without_plant_side_effect(self) -> None:
        controller = object.__new__(campaign.CausalDiscretePulseMPCController)
        controller.step = 10
        controller.r8r8_states = [
            {"step_index": index, "R": 0.75, "Z": 0.0, "Ip": 29779.724, "currents_a_tsc": [0.0] * 14}
            for index in range(11)
        ]
        controller.r8r8_actions = [[0.0] * 14 for _ in range(10)]
        controller.r8r8_decisions = []
        controller.r8r8_model_fault_count = 0
        controller.r8r8_selected_nonzero_count = 0
        controller.numeric_target_offsets = (0.0, 0.0, 0.0)
        controller.static_model = controller.action_model = {}
        controller.static_tube = controller.combined_tube = np.zeros((4, 5))
        controller.observer_cfg = controller.response_cfg = controller.r8r7_cfg = {}
        controller.r8r8_cfg = self.cfg
        current = controller.r8r8_states[-1]
        with mock.patch.object(campaign.mpc, "predict_candidates", side_effect=ValueError("fault")):
            action, trace = controller.action(current)
        np.testing.assert_array_equal(action, np.zeros(14))
        self.assertEqual(trace["r3c3t13s24d1r14r8r8_event"], "safe_zero_fallback")
        self.assertTrue(trace["r3c3t13s24d1r14r8r8_decision"]["model_fault"])
        self.assertEqual(controller.r8r8_model_fault_count, 1)

    def test_offline_fault_injection_exercises_nonfinite_and_exception_guards(self) -> None:
        rows = campaign._fault_injection(SimpleNamespace(cfg=self.cfg))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["safe_zero"] for row in rows))
        fault_rows = {row["case"]: row for row in rows}
        self.assertIn("non-finite", fault_rows["nonfinite_model_guard"]["fallback_reason"])
        self.assertIn("injected model exception", fault_rows["model_exception_guard"]["fallback_reason"])

    def test_parsers_are_fail_closed_and_independent_is_structural(self) -> None:
        primary_choices = next(
            action.choices for action in campaign._parser()._actions if action.dest == "command"
        )
        self.assertEqual(
            tuple(primary_choices),
            ("offline", "authorize-real", "run", "audit-primary", "finalize", "postprocess"),
        )
        audit_choices = next(
            action.choices for action in independent._parser()._actions if action.dest == "audit_kind"
        )
        self.assertEqual(tuple(audit_choices), ("offline", "final"))
        source = (
            ROOT
            / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r8_independent_forensics.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("causal_discrete_pulse_mpc as mpc", source)
        self.assertNotIn("causal_discrete_pulse_mpc_campaign as", source)

    def test_launcher_uses_only_existing_server_venv_and_direct_files(self) -> None:
        shell = (
            ROOT / "scripts/stage4_2r3c3t13s24d1r14r8r8_shell_common.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell)
        self.assertIn('WORKERS:-16', shell)
        launchers = "\n".join(
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "run_stage4_2r3c3t13s24d1r14r8r8_common.sh",
                "run_stage4_2r3c3t13s24d1r14r8r8_native.sh",
                "run_stage4_2r3c3t13s24d1r14r8r8_nohup.sh",
                "run_stage4_2r3c3t13s24d1r14r8r8_self_test.sh",
                "run_stage4_2r3c3t13s24d1r14r8r8_verify_package.sh",
            )
        )
        self.assertNotIn("python3", launchers)
        self.assertNotIn("tar ", launchers)
        self.assertNotIn("unzip", launchers)
        self.assertNotIn("zip ", launchers)


if __name__ == "__main__":
    unittest.main()
