from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t12_formal_gap_route_discriminator.py"
)
SPEC = importlib.util.spec_from_file_location(
    "stage4_2r3c3t12_formal_gap_route_discriminator", SCRIPT
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load T12 formal-gap route discriminator")
T12 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T12)


def _synthetic_evidence():
    distributions = [
        (True, True, 12),
        (True, False, 4),
        (False, True, 13),
        (False, False, 3),
    ]
    results = []
    conditions = []
    context_index = 0
    regression_added = False
    for baseline_pass, condition_pass, count in distributions:
        for _ in range(count):
            pair_id = f"p5_q{context_index:02d}_synthetic"
            key = {
                "pair_id": pair_id,
                "history_member": "minus_first",
                "target_id": "nominal",
                "actual_delay_steps": 0,
                "actual_slew_scale": 1.0,
            }
            baseline_margin = 0.1 if baseline_pass else -0.1
            results.append(
                {
                    **key,
                    "experiment_id": f"baseline_{context_index}",
                    "extended_baseline": True,
                    "probe_id": T12.BASELINE_PROBE_ID,
                    "probe_sign": 0,
                    "formal_contract_pass": baseline_pass,
                    "formal_minimum_signed_margin": baseline_margin,
                }
            )
            for probe_index in range(6):
                for sign in (-1, 1):
                    margin = baseline_margin + 0.01 * sign
                    if not baseline_pass:
                        margin = -0.05 - probe_index * 0.001
                    elif not regression_added:
                        margin = -0.01
                        regression_added = True
                    results.append(
                        {
                            **key,
                            "experiment_id": (
                                f"probe_{context_index}_{probe_index}_{sign}"
                            ),
                            "extended_baseline": False,
                            "probe_id": f"probe_{probe_index}",
                            "probe_sign": sign,
                            "formal_contract_pass": margin >= 0.0,
                            "formal_minimum_signed_margin": margin,
                        }
                    )
            conditions.append(
                {
                    **key,
                    "condition_number_pass": condition_pass,
                    "response_velocity_condition_number": (
                        10.0 if condition_pass else 30.0
                    ),
                }
            )
            context_index += 1
    return results, conditions


class Stage42R3C3T12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = (
            ROOT
            / "configs/stage4_2r3c3t12_formal_gap_route_discriminator_v1.json"
        )
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_design_is_strictly_read_only_and_no_model(self) -> None:
        T12._validate_design(self.config)
        analysis = self.config["analysis_contract"]
        execution = self.config["execution_contract"]
        scope = self.config["scientific_scope"]
        self.assertFalse(analysis["allow_column_normalization"])
        self.assertFalse(analysis["allow_column_rescaling"])
        self.assertFalse(analysis["allow_probe_combination"])
        self.assertFalse(analysis["allow_response_model_fit"])
        self.assertFalse(analysis["allow_formal_feasibility_optimization"])
        self.assertFalse(execution["ray_executed"])
        self.assertFalse(execution["gotsc_executed"])
        self.assertFalse(execution["tsc_executed"])
        self.assertFalse(scope["t11_verdict_may_change"])
        self.assertFalse(scope["t11_response_bank_created"])
        self.assertFalse(scope["r3c4_feasibility_model_created"])

    def test_design_change_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["analysis_contract"]["allow_column_normalization"] = True
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            T12._validate_design(changed)

    def test_cross_table_and_measured_corner_route_veto(self) -> None:
        results, conditions = _synthetic_evidence()
        audit, route = T12._analyze_reported_results(
            self.config, results, conditions
        )
        self.assertEqual(
            audit["cross_table"],
            {
                "formal_pass_condition_pass": 12,
                "formal_pass_condition_fail": 4,
                "formal_fail_condition_pass": 13,
                "formal_fail_condition_fail": 3,
            },
        )
        self.assertEqual(
            audit["reproduced_expectations"][
                "failed_baseline_single_probe_repair_total"
            ],
            0,
        )
        self.assertEqual(
            audit["reproduced_expectations"][
                "passing_baseline_single_probe_regression_total"
            ],
            1,
        )
        self.assertTrue(route["fixed_condition_first_route_vetoed"])
        self.assertFalse(
            route["all_failed_baselines_repaired_by_a_measured_single_probe"]
        )
        self.assertFalse(
            route["full_size_new_identification_campaign_authorized"]
        )
        self.assertFalse(route["r3c4_authorized"])

    def test_local_compact_hashes_match_when_present(self) -> None:
        compact = (
            ROOT
            / "docs/codex/audits/stage4_2r3c3t11_persistent_step_response_identification_20260801_40944f9/server_compact"
        )
        if not compact.is_dir():
            self.skipTest("T11 compact evidence is not present")
        source = self.config["source_contract"]
        names = {
            "stage4_2r3c3t11_config.resolved.json": "t11_config_sha256",
            "stage4_2r3c3t11_manifest.json": "t11_manifest_sha256",
            "stage4_2r3c3t11_state.json": "t11_state_sha256",
            "stage4_2r3c3t11_summary.json": "t11_summary_sha256",
            "condition_number_results.json": "t11_condition_results_sha256",
            "central_response_results.json": "t11_central_results_sha256",
            "matched_hidden_history_results.json": (
                "t11_matched_history_results_sha256"
            ),
            "stage4_2r3c3t11_verdict.json": "t11_verdict_sha256",
            "stage4_2r3c3t11_server_audit.json": "t11_server_audit_sha256",
            "stage4_2r3c3t11_snapshot_audit.json": (
                "t11_snapshot_audit_sha256"
            ),
        }
        for name, field in names.items():
            path = compact / name
            if path.is_file():
                self.assertEqual(T12._sha256(path), source[field])

    def test_launchers_are_offline_and_stage_specific(self) -> None:
        texts = [
            (ROOT / name).read_text(encoding="utf-8")
            for name in (
                "run_stage4_2r3c3t12_common.sh",
                "run_stage4_2r3c3t12_offline.sh",
                "run_stage4_2r3c3t12_nohup.sh",
                "scripts/stage4_2r3c3t12_shell_common.sh",
            )
        ]
        combined = "\n".join(texts)
        self.assertNotIn("pkill", combined)
        self.assertNotIn("ray stop", combined)
        self.assertNotIn("--resume", combined)
        self.assertIn("read-only source audit", combined)
        self.assertIn("stage4_2r3c3t12", combined)

    def test_design_document_preserves_t11_and_blocks_learning(self) -> None:
        design = (
            ROOT
            / "docs/codex/reports/STAGE4_2R3C3T12_FORMAL_GAP_ROUTE_DISCRIMINATOR_DESIGN.md"
        ).read_text(encoding="utf-8")
        self.assertIn("does not reinterpret T11", design)
        self.assertIn("No response columns may be added", design)
        self.assertIn("R3c4, BC, DAgger", design)


if __name__ == "__main__":
    unittest.main()
