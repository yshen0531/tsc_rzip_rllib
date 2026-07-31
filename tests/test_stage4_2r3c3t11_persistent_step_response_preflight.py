from __future__ import annotations

import importlib.util
import copy
import json
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/codex/audit_tools/stage4_2r3c3t11_persistent_step_response_preflight.py"
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t11_persistent_step_response_preflight", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T11 preflight")
T11 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T11)


class Stage42R3C3T11PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = ROOT / "configs/stage4_2r3c3t11_persistent_step_response_preflight_v1.json"
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_design_and_available_source_hashes(self) -> None:
        T11._validate_design(self.config)
        source = self.config["source_contract"]
        checks = {
            ROOT / "docs/codex/audit_tools/stage4_2r3c3t6_new_direction_preflight.py": "t6_preflight_tool_sha256",
            ROOT / "docs/codex/audits/stage4_2r3c3t6_new_direction_preflight_20260731_428a0bd/stage4_2r3c3t6_new_direction_preflight_v1.json": "t6_preflight_sha256",
            ROOT / "docs/codex/audits/stage4_2r3c3t9_pc3_mixed_interaction_preflight_20260731_cbb970b/stage4_2r3c3t9_pc3_mixed_interaction_preflight_v1.json": "t9_preflight_sha256",
            ROOT / "docs/codex/audits/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505/server_compact/stage4_2r3c3t10_manifest_v1.json": "t10_manifest_sha256",
            ROOT / "docs/codex/audits/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505/server_compact/stage4_2r3c3t10_audit_v1.json": "t10_audit_sha256",
            ROOT / "docs/codex/audits/stage4_2r3c3t10_interaction_aware_feasibility_20260731_125505/server_compact/stage4_2r3c3t10_feasibility_v1.json": "t10_feasibility_sha256",
        }
        for path, field in checks.items():
            self.assertEqual(T11._sha256(path), source[field])
        self.assertEqual(
            source["t3_eight_basis_controller_bank_sha256"],
            "6328ef4116ea5a2ecac66d04583fb92af7830ad5ff6ea484486524cbd2021e86",
        )

    def test_frozen_design_rejects_scientific_weakening(self) -> None:
        mutations = [
            ("persistent_step_contract", "hidden_history_or_pair_label_input_allowed", True),
            ("persistent_step_contract", "source_result_or_action_input_allowed", True),
            ("action_preflight_gate", "minimum_new_column_residual_norm_outside_existing_span", 0.0),
            ("prospective_real_identification_contract", "maximum_current_utilization", 1.0),
            ("formal_timing_contract", "normal_arrival_deadline_step", 26),
            ("scientific_scope", "bc_dagger_or_rl_allowed", True),
        ]
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                changed = copy.deepcopy(self.config)
                changed[section][field] = value
                with self.assertRaisesRegex(ValueError, "frozen design changed"):
                    T11._validate_design(changed)

    def test_all_six_public_schedules_are_exact_and_zero_net(self) -> None:
        for delay in (0, 2):
            probes = [
                T11._persistent_step_payload(
                    mode=mode,
                    first_effect_state=effect,
                    delay=delay,
                    cfg=self.config,
                )
                for effect in (3, 17)
                for mode in (0, 1, 2)
            ]
            self.assertEqual(len({p["probe_id"] for p in probes}), 6)
            for probe in probes:
                self.assertEqual(probe["nonzero_issue_count"], 7)
                self.assertTrue(
                    np.allclose(probe["requested_full_net"], np.zeros(3), atol=1e-12)
                )
                self.assertLessEqual(probe["formal_l2_norm"], 0.015)
                self.assertLessEqual(probe["formal_max_abs_component"], 0.0075)
                self.assertEqual(probe["first_cancellation_effect_state"], 39)
                self.assertEqual(probe["last_cancellation_effect_state"], 44)

    def test_new_formal_columns_have_rank_six(self) -> None:
        for delay, hold in ((0, 35), (2, 37)):
            columns = []
            for effect in (3, 17):
                for mode in (0, 1, 2):
                    probe = T11._persistent_step_payload(
                        mode=mode,
                        first_effect_state=effect,
                        delay=delay,
                        cfg=self.config,
                    )
                    columns.append(T11._formal_schedule(probe, hold).reshape(-1))
            self.assertEqual(np.linalg.matrix_rank(np.column_stack(columns)), 6)

    def test_rank_gate_is_invariant_to_column_amplitude(self) -> None:
        scaled_identity = np.diag([1.0e6, 1.0e-12, 1.0])
        self.assertLess(np.linalg.matrix_rank(scaled_identity), 3)
        self.assertEqual(np.linalg.matrix_rank(T11._normalized(scaled_identity)), 3)

    def test_scope_and_task_identity_are_conservative(self) -> None:
        real = self.config["prospective_real_identification_contract"]
        scope = self.config["scientific_scope"]
        self.assertEqual(real["total_task_count"], 416)
        self.assertEqual(real["extended_baseline_count"] + real["signed_probe_count"], 416)
        self.assertFalse(scope["preflight_executes_real_tsc"])
        self.assertFalse(scope["action_schedule_novelty_is_plant_response_validation"])
        self.assertFalse(scope["controller_implementation_authorized_by_preflight"])
        self.assertFalse(scope["bc_dagger_or_rl_allowed"])

    def test_design_report_preserves_timing_and_learning_veto(self) -> None:
        text = (
            ROOT / "docs/codex/reports/STAGE4_2R3C3T11_PERSISTENT_STEP_PREFLIGHT_DESIGN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("250/270 ms arrival", text)
        self.assertIn("350/370 ms hold", text)
        self.assertIn("R3c4, BC, DAgger, and residual RL", text)
        self.assertIn("Two initial T11 invocations stopped", text)

    def test_launcher_uses_the_exact_t9_eight_basis_source(self) -> None:
        text = (ROOT / "run_stage4_2r3c3t11_preflight.sh").read_text(encoding="utf-8")
        self.assertIn("stage4_2r3c3t3_eight_basis_controller_bank_v1.json", text)
        self.assertNotIn("stage4_2r3c3t7_controller_bank_v1.json", text)


if __name__ == "__main__":
    unittest.main()
