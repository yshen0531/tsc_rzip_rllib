from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r49_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r6_direction0_replacement_sentinel as r6,
    stage4_2r3c3t13s24d1r14r8r49_q0_to_transport_causal_bridge_identification_sentinel as r49,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / (
    "stage4_2r3c3t13s24d1r14r8r49_"
    "q0_to_transport_causal_bridge_identification_sentinel_370ms.json"
)


class R8R49Q0TransportBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.matrix = np.asarray(
            [
                [0.06036182177162116, 0.06409209376301149, -0.37110098238653283, 0.13657703474397473],
                [-3.921547352685623, -3.280604324442652, 4.73169603859497, -3.6727205346962286],
                [0.49109976246409964, 0.13593338869530727, -0.035003869827120934, -0.3079668079336082],
                [-0.18672754749097395, -0.17590787535526847, -0.08626957714716102, 0.19464202995789268],
            ],
            dtype=float,
        )
        candidate_ids = self.cfg["matrix_contract"]["candidate_ids"]
        q = (
            [0.0, 0.0, 0.0, 0.0], [-1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0], [0.0, 0.0, 0.0, -1.0],
            [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.5, 0.0],
            [0.0, 0.0, 0.75, 0.0], [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 1.25, 0.0], [0.0, 0.0, 1.5, 0.0],
            [0.0, -0.5, 0.0, 0.0], [0.0, -0.75, 0.0, 0.0],
            [0.0, -1.0, 0.0, 0.0], [0.0, -1.25, 0.0, 0.0],
            [0.0, -1.5, 0.0, 0.0],
        )
        self.candidates = [
            {"index": index, "id": candidate_id, "q": np.asarray(value, dtype=float)}
            for index, (candidate_id, value) in enumerate(zip(candidate_ids, q))
        ]

    def test_frozen_config_and_design_hash(self) -> None:
        r49.validate_config(self.cfg, project_root=ROOT)
        design = ROOT / self.cfg["design_document"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        self.assertEqual(self.cfg["matrix_contract"]["trajectory_count"], 256)
        self.assertTrue(self.cfg["formal_contract"]["formal_tracking_diagnostic_only"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])
        self.assertTrue(all(
            len(value) == 64
            for key, value in self.cfg["source_r8r48"].items()
            if key.endswith("_sha256")
        ))

    def test_mutations_fail_closed(self) -> None:
        for section, key, value in (
            ("schedule_contract", "candidate_issue_task_step", 13),
            ("controller_contract", "maximum_incremental_normalized_action_linf", 0.26),
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("scientific_scope", "model_fit_allowed", True),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design changed"):
                r49.validate_config(changed, project_root=ROOT)

        changed = copy.deepcopy(self.cfg)
        changed["source_r8r48"]["primary_detailed_sha256"] = "0" * 63
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            r49.validate_config(changed, project_root=ROOT)

    def test_build_specs_is_exact_16_by_16_nonzero_matrix(self) -> None:
        baselines = [
            {
                "experiment_id": f"baseline_{index:02d}",
                "pair_id": f"pair_{index // 2}",
                "history_member": "minus_first" if index % 2 == 0 else "plus_first",
                "horizon_steps": 35,
                "formal_horizon_steps": 35,
            }
            for index in range(16)
        ]
        source_cfg = {"candidate_contract": {"canonical_matrix_columns": self.matrix.tolist()}}
        ctx = SimpleNamespace(r8r48_ctx=SimpleNamespace(source_ctx=SimpleNamespace(cfg=source_cfg)))
        with mock.patch.object(r49, "_source_baselines", return_value=(baselines, {})), mock.patch.object(
            r49.r8r31, "_candidate_rows", return_value=self.candidates
        ):
            specs = r49.build_specs(ctx)
        self.assertEqual(len(specs), 256)
        self.assertNotIn("q0", {row["r8r49_candidate_id"] for row in specs})
        self.assertEqual({row["r8r49_candidate_index"] for row in specs}, set(range(1, 17)))
        self.assertTrue(all(row["r8r49_allowed_in_expert_dataset"] is False for row in specs))
        for row in specs:
            expected = self.matrix @ np.asarray(row["r8r49_candidate_q"], dtype=float)
            self.assertTrue(np.array_equal(expected, np.asarray(row["r8r49_requested_coordinate"])))

    def test_controller_freezes_steps_and_explicit_coordinate(self) -> None:
        spec = {
            "r8r49_candidate_id": "u1p25",
            "r8r49_requested_coordinate": (self.matrix @ np.asarray([0.0, 0.0, 1.25, 0.0])).tolist(),
        }
        contract = copy.deepcopy(self.cfg["controller_contract"])
        contract["requested_coordinate_matrix_columns"] = self.matrix.tolist()
        with mock.patch.object(r6.d1r11.SequentialAmplitudeCodedProbeController, "__init__", return_value=None) as parent, mock.patch.object(
            r6, "_controller_source_spec", return_value={}
        ):
            controller = r49.BridgeController(object(), {}, {}, {}, {}, {}, {}, {}, contract, spec=spec)
        self.assertEqual(controller.r8r49_candidate_id, "u1p25")
        self.assertEqual(parent.call_count, 1)
        self.assertEqual(r49.ISSUE_STEP, 12)
        self.assertEqual(r49.RETURN_STEP, 14)

    def test_controller_uses_exact_issue_return_and_refresh_primitives(self) -> None:
        source = inspect.getsource(r49.BridgeController)
        self.assertIn("_construct_coordinate_issue", source)
        self.assertIn("_return_event", source)
        self.assertIn("_refresh_event", source)
        self.assertNotIn("-self.r8r49", source)

    def test_observe_hold_is_exact_zero_and_fail_closed(self) -> None:
        class Actuator:
            minimum_current_a_tsc = tuple([-100.0] * 14)
            maximum_current_a_tsc = tuple([100.0] * 14)

            @staticmethod
            def apply(currents, action):
                return SimpleNamespace(
                    card15_fields=tuple([" 0.000E+00"] * 14),
                    action_saturated=tuple([False] * 14),
                    current_limit_clipped=tuple([False] * 14),
                    nominal_readback_current_a_tsc=tuple(map(float, currents)),
                )

        event = r49._observe_event(
            task_step=11, currents=np.zeros(14), target_fields=[" 0.000E+00"] * 14,
            actuator=Actuator(), contract=self.cfg["controller_contract"], event="q0_observe_hold",
        )
        self.assertTrue(event["passed"])
        self.assertEqual(event["action_norm_tsc"], [0.0] * 14)
        changed = r49._observe_event(
            task_step=11, currents=np.zeros(14), target_fields=[" 1.000E+00"] * 14,
            actuator=Actuator(), contract=self.cfg["controller_contract"], event="q0_observe_hold",
        )
        self.assertFalse(changed["passed"])

    def test_prefix_digest_excludes_runtime_timing_but_includes_visible_current_and_trace(self) -> None:
        states = [
            {"step_index": index, "R": 1.0, "Z": 2.0, "Ip": 3.0,
             "currents_a_tsc": [0.0] * 14, "gotsc_subprocess_s": 1.0, "step_total_s": 2.0}
            for index in range(13)
        ]
        result = {"trajectory": states, "controller_trace": [{"action_norm_tsc": [0.0] * 14} for _ in range(12)]}
        left = r49._prefix_payload(result)
        changed = copy.deepcopy(result)
        changed["trajectory"][5]["gotsc_subprocess_s"] = 99.0
        self.assertEqual(left, r49._prefix_payload(changed))
        changed["trajectory"][5]["R"] += 1e-12
        self.assertNotEqual(left, r49._prefix_payload(changed))
        changed = copy.deepcopy(result)
        changed["controller_trace"][11]["action_norm_tsc"][0] = 1e-12
        self.assertNotEqual(left, r49._prefix_payload(changed))

    def test_routes_distinguish_source_offline_execution_safety_and_identification(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 5)
        self.assertIn("BLOCKED_BY_SOURCE", routes["source_blocked"])
        self.assertIn("NO_REAL_TSC", routes["offline_fail"])
        self.assertIn("EXECUTION_FAIL_STOP", routes["execution_fail"])
        self.assertIn("SAFETY_FAIL_REDESIGN", routes["safety_fail"])
        self.assertIn("MODEL_PREFLIGHT_REQUIRED", routes["pass"])

    def test_independent_has_separate_offline_and_raw_entrypoints(self) -> None:
        self.assertIsNot(independent._offline, r49.prepare_offline)
        self.assertIsNot(independent._raw, r49.audit_raw)
        source = inspect.getsource(independent._raw)
        self.assertIn("response_digest", source)
        self.assertIn("primary_agreement", source)

    def test_runner_uses_exported_source_locator_names(self) -> None:
        runner = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r49_common.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("stage4_2r3c3t13s21_find_source_s21", runner)
        for suffix in (
            "find_source_s21", "find_source_s23r1", "find_source_s24",
            "find_source_d1r9_v1", "find_source_d1r9_v2",
            "find_source_d1r10", "find_source_d1r10_audit",
        ):
            self.assertIn(f"stage4_2r3c3t13s24d1r11_{suffix}", runner)


if __name__ == "__main__":
    unittest.main()
