from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r51r4d4_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel
    as d4,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r51r4d4_center_bridged_two_pulse_response_sentinel_370ms.json"
ORIGINAL_DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D4_CENTER_BRIDGED_TWO_PULSE_RESPONSE_SENTINEL_DESIGN.md"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D4_RUNTIME_HOTFIX_FRESH_RUN_DESIGN.md"
D5_DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R8R51R4D5_CAUSAL_TWO_DECISION_MODEL_CONTROLLER_PREFLIGHT_DESIGN.md"
ACTION_EQUIVALENCE_CONTRACT = ROOT / d4.ACTION_EQUIVALENCE_CONTRACT
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r51r4d4_common.sh"


def _config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _source_specs() -> list[dict]:
    rows = []
    for context_index in range(10):
        baseline_id = f"r8r7_baseline_{context_index if context_index < 8 else context_index + 4:02d}"
        for first_index, first_id in enumerate(d4.CANDIDATE_IDS):
            for second_index, second_id in enumerate(d4.CANDIDATE_IDS):
                rows.append(
                    {
                        "experiment_id": f"r8r51r4d3_c{context_index:02d}_{first_id}_then_{second_id}",
                        "source_r8r7_baseline_experiment_id": baseline_id,
                        "context_index": context_index,
                        "pair_id": f"pair_{context_index // 2:02d}",
                        "history_member": "a" if context_index % 2 == 0 else "b",
                        "first_candidate_id": first_id,
                        "second_candidate_id": second_id,
                        "first_candidate_index": first_index,
                        "second_candidate_index": second_index,
                        "first_requested_coordinate": [float(first_index), 0.0, 0.0, 0.0],
                        "second_requested_coordinate": [float(second_index), 0.0, 0.0, 0.0],
                        "first_source_experiment_id": f"source_{context_index}_{first_id}",
                        "second_source_experiment_id": f"source_{context_index}_{second_id}",
                        "horizon_steps": 37 if context_index < 6 else 35,
                        "allowed_in_expert_dataset": False,
                    }
                )
    return rows


class TestR51R4D4CenterBridgedTwoPulseResponseSentinel(unittest.TestCase):
    def test_frozen_config_design_and_conditional_d5_authenticate(self) -> None:
        cfg = _config()
        d4.validate_config(cfg, ROOT)
        self.assertEqual(d4._sha(DESIGN), cfg["design_document_sha256"])
        self.assertEqual(
            d4._sha(ORIGINAL_DESIGN), cfg["original_design_document_sha256"]
        )
        self.assertEqual(cfg["design_checkpoint"], "bcb4c5f")
        self.assertTrue(cfg["identity"].endswith("runtime_hotfix1"))
        self.assertEqual(d4._sha(D5_DESIGN), cfg["conditional_d5_design_sha256"])
        self.assertEqual(cfg["conditional_d5_design_checkpoint"], "dd764cb")
        self.assertEqual(cfg["matrix_contract"]["trajectory_count"], 250)
        self.assertEqual(cfg["known_aggregate_contract"]["maximum_successful_plant_steps"], 9050)

    def test_mutating_load_bearing_gate_is_rejected(self) -> None:
        cfg = _config()
        mutated = copy.deepcopy(cfg)
        mutated["scientific_gate"]["minimum_repaired_failed_baseline_count"] = 0
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d4.validate_config(mutated, ROOT)
        mutated = copy.deepcopy(cfg)
        mutated["failed_attempt_contract"]["plant_step_count"] = 0
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d4.validate_config(mutated, ROOT)
        mutated = copy.deepcopy(cfg)
        mutated["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d4.validate_config(mutated, ROOT)

    def test_complete_ordered_matrix_preserves_no_learning_and_no_label_inputs(self) -> None:
        source = _source_specs()
        baselines = [
            {
                "experiment_id": baseline_id,
                "horizon_steps": 37 if index < 6 else 35,
                "source_only": index,
            }
            for index, baseline_id in enumerate(
                [f"r8r7_baseline_{i:02d}" for i in (*range(8), 12, 13)]
            )
        ]
        ctx = SimpleNamespace(d3_stage=ROOT / ".codex_tmp" / "unused_d3", r4_ctx=SimpleNamespace(base_ctx=None))
        with (
            mock.patch.object(d4, "_read", return_value=source),
            mock.patch.object(d4.r4.r51, "_source_baselines", return_value=(baselines, {})),
        ):
            specs = d4.build_specs(ctx)
        self.assertEqual(len(specs), 250)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 250)
        self.assertEqual(
            len({(row["context_index"], row["first_candidate_id"], row["second_candidate_id"]) for row in specs}),
            250,
        )
        self.assertTrue(all(row["stage"] == d4.STAGE for row in specs))
        self.assertTrue(all(row["r8r51r4d4_allowed_in_expert_dataset"] is False for row in specs))
        self.assertTrue(all(row["pair_or_history_label_available_to_controller"] is False for row in specs))
        self.assertTrue(all(row["source_result_available_to_controller"] is False for row in specs))
        self.assertTrue(all(row["future_measurement_count"] == 0 for row in specs))

    def test_clock_actions_and_safe_stop_are_encoded_in_real_controller(self) -> None:
        cfg = _config()
        schedule = cfg["schedule_contract"]
        self.assertEqual(
            [schedule[key] for key in (
                "q0_issue_task_step", "first_issue_task_step", "first_return_task_step",
                "center_bridge_hold_task_step", "second_issue_task_step", "second_return_task_step",
            )],
            [10, 12, 16, 17, 18, 22],
        )
        source = Path(d4.TwoPulseController.__code__.co_filename if hasattr(d4.TwoPulseController, "__code__") else d4.__file__).read_text(encoding="utf-8")
        self.assertIn('event="exact_q0_center_bridge_hold"', source)
        self.assertIn('event["event"] = "second_center_bridged_candidate_issue"', source)
        self.assertIn('event["event"] = "second_pulse_stored_center_return"', source)
        self.assertIn("pre_action_visible_state_safety_failure", source)
        self.assertIn("controller_action_safety_gate_failure", source)
        self.assertIn("runner.cleanup_episode_workspace", source)

    def test_live_controller_uses_inherited_r51r1_state_namespace(self) -> None:
        spec = {
            "first_candidate_id": "d0m",
            "first_requested_coordinate": [-0.5, 0.0, 0.0, 0.0],
            "second_candidate_id": "d1p",
            "second_requested_coordinate": [0.0, 0.5, 0.0, 0.0],
        }
        with mock.patch.object(d4.r4.SustainedDwellController, "__init__", return_value=None):
            controller = d4.TwoPulseController(spec=spec)
        self.assertEqual(controller.r8r51r1_candidate_id, "d0m")
        self.assertEqual(controller.r8r51r1_requested_coordinate.tolist(), spec["first_requested_coordinate"])
        source = Path(d4.__file__).read_text(encoding="utf-8")
        for stale in (
            "self.r8r51_center_fields", "self.r8r51_contract",
            "self.r8r51_candidate_id", "self.r8r51_requested_coordinate",
            "self.r8r51_issue_event",
        ):
            self.assertNotIn(stale, source)

        controller.r8r51r1_center_fields = ["1.000E+00"] * d4.N_COILS
        controller.r8r51r1_contract = {}
        controller.r8r51r1_issue_event = None
        controller.actuator = object()
        observed = []
        captures = []

        def observe(**kwargs):
            observed.append(kwargs)
            return {"passed": True, "criteria": {"test": True}, "action_norm_tsc": [0.0] * d4.N_COILS}

        def q0(this, currents):
            this.r8r51r1_center_fields = ["1.000E+00"] * d4.N_COILS
            return d4.np.zeros(d4.N_COILS), {"passed": True, "criteria": {"test": True}}

        def issue(this, currents):
            captures.append((this.r8r51r1_candidate_id, this.r8r51r1_requested_coordinate.tolist()))
            this.r8r51r1_issue_event = {"target_card15_fields": ["2.000E+00"] * d4.N_COILS}
            return d4.np.zeros(d4.N_COILS), {"passed": True, "criteria": {"test": True}}

        def returned(this, currents):
            return d4.np.zeros(d4.N_COILS), {"passed": True, "criteria": {"test": True}}

        def refresh(this, currents):
            return d4.np.zeros(d4.N_COILS), {"passed": True, "criteria": {"test": True}}

        with (
            mock.patch.object(d4.TwoPulseController, "_q0", new=q0),
            mock.patch.object(d4.TwoPulseController, "_issue_candidate", new=issue),
            mock.patch.object(d4.TwoPulseController, "_return", new=returned),
            mock.patch.object(d4.TwoPulseController, "_center_refresh", new=refresh),
            mock.patch.object(d4.r4.r51, "_observe_event", side_effect=observe),
            mock.patch.object(
                d4.r4.r51.r6,
                "_trace_template",
                return_value={"action_norm_tsc": [0.0] * d4.N_COILS},
            ),
        ):
            event_names = []
            for step in range(d4.Q0_STEP, d4.SECOND_RETURN + 2):
                controller.step = step
                action, trace = controller.action(
                    {"step_index": step, "currents_a_tsc": [0.0] * d4.N_COILS}
                )
                self.assertEqual(action.tolist(), [0.0] * d4.N_COILS)
                event_names.append(trace["r3c3t13s24d1r14r8r51r4d4_event"])
        self.assertEqual(event_names, [
            "q0_exact_issue", "q0_observe_hold", "first_candidate_issue",
            "first_candidate_hold", "first_candidate_hold", "first_candidate_hold",
            "first_stored_center_return", "center_bridge_hold", "second_candidate_issue",
            "second_candidate_hold", "second_candidate_hold", "second_candidate_hold",
            "second_stored_center_return", "center_refresh",
        ])
        self.assertEqual(observed[0]["target_fields"], controller.r8r51r1_center_fields)
        self.assertEqual(observed[0]["contract"], controller.r8r51r1_contract)
        self.assertEqual(captures, [
            ("d0m", spec["first_requested_coordinate"]),
            ("d1p", spec["second_requested_coordinate"]),
        ])

    def test_raw_audit_uses_numerical_current_equivalence_without_weakening_actions(self) -> None:
        source = Path(d4.__file__).read_text(encoding="utf-8")
        self.assertEqual(d4.CURRENT_ATOL_A, 1e-12)
        self.assertIn("np.allclose(physical, nominal, rtol=0.0, atol=CURRENT_ATOL_A", source)
        self.assertIn('list(detail.get("action_norm_tsc") or []) == list(trace[step]["action_norm_tsc"])', source)
        independent_source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertIn("difference <= d4.CURRENT_ATOL_A", independent_source)

    def test_action_reporting_repair_accepts_only_frozen_numeric_equivalence(self) -> None:
        exact = {
            "task_step": 12,
            "event": "first_candidate_issue",
            "candidate_id": "d0m",
            "requested_coordinate": [-0.5, 0.0, 0.0, 0.0],
            "action_norm_tsc": [0.1] * d4.N_COILS,
            "target_card15_fields": ["1.000E+00"] * d4.N_COILS,
            "passed": True,
            "criteria": {"exact_card15": True},
        }
        rounded = copy.deepcopy(exact)
        rounded["action_norm_tsc"][0] += 1e-14
        self.assertFalse(d4._semantic_event_equal(rounded, exact))
        self.assertFalse(independent._event_equal(rounded, exact))
        self.assertTrue(
            d4._semantic_event_equal(
                rounded, exact, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )
        self.assertTrue(
            independent._event_equal(
                rounded, exact, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )

        outside = copy.deepcopy(exact)
        outside["action_norm_tsc"][0] += 1.1e-12
        self.assertFalse(
            d4._semantic_event_equal(
                outside, exact, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )
        self.assertFalse(
            independent._event_equal(
                outside, exact, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )

    def test_action_reporting_repair_fails_closed_on_shape_nonfinite_or_discrete_change(self) -> None:
        expected = {
            "event": "center_refresh",
            "action_norm_tsc": [0.0] * d4.N_COILS,
            "passed": True,
            "criteria": {"refresh": True},
        }
        for action in (
            [0.0] * (d4.N_COILS - 1),
            [float("nan")] + [0.0] * (d4.N_COILS - 1),
            [float("inf")] + [0.0] * (d4.N_COILS - 1),
        ):
            actual = copy.deepcopy(expected)
            actual["action_norm_tsc"] = action
            self.assertFalse(
                d4._semantic_event_equal(
                    actual, expected, action_atol=d4.ACTION_EQUIVALENCE_ATOL
                )
            )
            self.assertFalse(
                independent._event_equal(
                    actual, expected, action_atol=d4.ACTION_EQUIVALENCE_ATOL
                )
            )
        changed = copy.deepcopy(expected)
        changed["event"] = "second_candidate_issue"
        self.assertFalse(
            d4._semantic_event_equal(
                changed, expected, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )
        self.assertFalse(
            independent._event_equal(
                changed, expected, action_atol=d4.ACTION_EQUIVALENCE_ATOL
            )
        )

    def test_action_reporting_contract_and_artifact_names_are_frozen(self) -> None:
        self.assertEqual(d4.ACTION_EQUIVALENCE_ATOL, 1e-12)
        self.assertEqual(d4.ACTION_EQUIVALENCE_EXPECTED_EVENT_COUNT, 6550)
        self.assertEqual(d4.ACTION_EQUIVALENCE_EXPECTED_BINARY_EXACT_COUNT, 3070)
        self.assertEqual(
            d4._sha(ACTION_EQUIVALENCE_CONTRACT),
            d4.ACTION_EQUIVALENCE_CONTRACT_SHA256,
        )
        self.assertNotEqual(
            d4.ACTION_EQUIVALENCE_PRIMARY_NAME, "raw_integrity_primary.json"
        )
        self.assertNotEqual(
            d4.ACTION_EQUIVALENCE_INDEPENDENT_NAME,
            "raw_integrity_independent.json",
        )
        state = {"action_equivalence_reporting_hotfix_authorized": True}
        ctx = SimpleNamespace(paths=SimpleNamespace(analysis=ROOT / ".codex_tmp"))
        self.assertEqual(
            d4._primary_integrity_path(ctx, state).name,
            d4.ACTION_EQUIVALENCE_PRIMARY_NAME,
        )
        self.assertEqual(
            d4._independent_integrity_path(ctx, state).name,
            d4.ACTION_EQUIVALENCE_INDEPENDENT_NAME,
        )

    def test_failure_reporting_uses_json_null_for_unavailable_current_difference(self) -> None:
        primary_source = Path(d4.__file__).read_text(encoding="utf-8")
        independent_source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertIn("max(current_differences) if current_differences else None", primary_source)
        self.assertNotIn("max(current_differences, default=math.inf)", primary_source)
        self.assertIn("0.0 if sequence else None", independent_source)
        self.assertNotIn(
            'max(float(row["maximum_event_nominal_current_difference_a"]) for row in rows)',
            primary_source,
        )

    def test_independent_path_does_not_delegate_primary_construction_or_formal_metric(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("d4._events", source)
        self.assertNotIn("d4._offline_construction", source)
        self.assertNotIn("d4._formal_authority", source)
        self.assertIn("d3_ind._construct_row", source)
        self.assertIn("r51r3_ind.scalar_formal_metric", source)
        self.assertIn("def _authority(", source)

    def test_independent_authority_requires_real_repair_and_oracle_gain(self) -> None:
        rows = []
        for context in range(2):
            common = {"pair_id": "pair_00", "history_member": "ab"[context]}
            rows.append({**common, "partition": "baseline", "formal_contract_pass": False,
                         "formal_minimum_signed_margin": -0.2, "formal_mean_signed_margin": -0.1})
            for first in range(2):
                for second in range(2):
                    repaired = context == 0 and first == second == 1
                    rows.append({**common, "partition": "candidate",
                                 "first_candidate_id": str(first), "second_candidate_id": str(second),
                                 "first_candidate_index": first, "second_candidate_index": second,
                                 "formal_contract_pass": repaired,
                                 "formal_minimum_signed_margin": 0.01 if repaired else -0.1,
                                 "formal_mean_signed_margin": 0.02 if repaired else -0.05})
        result = independent._authority(rows, baseline_pass=6)
        self.assertEqual(result["repaired_failed_baseline_count"], 1)
        self.assertEqual(result["measured_oracle_formal_pass_count"], 7)

    def test_launcher_exposes_only_frozen_phases_and_existing_venv(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn('--r51r4d3-run "${R51R4D3_RUN}"', source)
        self.assertIn('--failed-r51r4d4-run "${FAILED_R51R4D4_RUN}"', source)
        self.assertIn("independent-raw|repair-raw-primary|repair-raw-independent|authorize-raw-repair|finalize-primary", source)
        self.assertIn("--backend \"${BACKEND}\" --resume", source)
        self.assertNotIn("gotsc", source)
        self.assertNotIn("expert", source.lower().split("probes forbidden from learning")[0])
        command_action = next(
            action for action in d4._parser()._actions if action.dest == "command"
        )
        self.assertTrue(
            {
                "repair-raw-primary",
                "repair-raw-independent",
                "authorize-raw-repair",
            }.issubset(set(command_action.choices))
        )

    def test_routes_and_scope_do_not_claim_mpc_or_gate_a(self) -> None:
        cfg = _config()
        self.assertEqual(set(cfg["routes"]), {
            "source_blocked", "offline_fail", "execution_fail", "authority_insufficient", "pass"
        })
        self.assertTrue(cfg["routes"]["offline_fail"].endswith("NO_REAL_TSC"))
        self.assertTrue(cfg["routes"]["pass"].endswith("R51R4D5_MODEL_CONTROLLER_PREFLIGHT_REQUIRED"))
        scope = cfg["scientific_scope"]
        self.assertTrue(scope["identification_only"])
        self.assertFalse(scope["model_fit_allowed"])
        self.assertFalse(scope["real_mpc_executed"])
        self.assertFalse(scope["gate_a_qualified"])
        self.assertFalse(scope["expert_data_allowed"])
        self.assertFalse(scope["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
