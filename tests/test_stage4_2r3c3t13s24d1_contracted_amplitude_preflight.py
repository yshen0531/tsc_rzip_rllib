import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1_contracted_amplitude_preflight as d1,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s24d1_contracted_amplitude_preflight_v1.json"
S23R1_CONFIG = ROOT / "configs" / "stage4_2r3c3t13s23r1_amplitude_coded_hadamard_preflight_v1.json"
DESIGN = ROOT / "docs" / "codex" / "reports" / "STAGE4_2R3C3T13S24D1_CONTRACTED_AMPLITUDE_PREFLIGHT_DESIGN.md"


class Stage42R3C3T13S24D1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.s23r1_cfg = json.loads(S23R1_CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_document_validate(self):
        d1._validate_design(self.cfg)
        self.assertEqual(d1._sha256(DESIGN), self.cfg["design_document_sha256"])

    def test_amplitude_or_formal_timing_change_is_rejected(self):
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["canonical_pattern_amplitudes"]["++--"] = 0.224
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d1._validate_design(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            d1._validate_design(changed)

    def test_contracted_matrix_has_preregistered_geometry(self):
        replay = d1._replay_config(self.s23r1_cfg, self.cfg)
        matrix = d1.r1._requested_matrix(replay)
        self.assertEqual(matrix.shape, (24, 16))
        np.testing.assert_array_equal(matrix[16:], -matrix[:8])
        metrics = d1.r1.s23._matrix_metrics(matrix, replay)
        self.assertEqual(metrics["global_rank"], 16)
        self.assertAlmostEqual(metrics["global_normalized_condition"], 1.57134840263677)
        self.assertAlmostEqual(
            max(row["normalized_condition"] for row in metrics["slot_rows"]),
            1.1111111111111112,
        )

    def test_source_applicability_rejects_any_quarter_amplitude_failure(self):
        source = self.cfg["source_contract"]
        active = {
            "strict_parse_count": 600,
            "parse_errors": [], "unexpected_ids": [], "missing_ids": [],
            "inventory": {
                "count": 600, "total_bytes": source["active_raw_total_bytes"],
                "digest": source["active_raw_inventory_digest"],
            },
            "baseline_complete_success_count": 24,
            "sequence_complete_success_count": 522,
            "sequence_failure_count": 54,
            "failure_classes": {d1.ALLOWED_FAILURE: 54},
            "forensic_integrity_pass_count": 600,
            "identity_and_spec_exact_count": 600,
            "restart_exact_count": 600,
            "causal_trace_pass_count": 600,
            "runtime_prefix_pass_count": 600,
            "calibration_pass_count": 600,
            "event_prefix_pass_count": 600,
            "cancellation_event_counts_by_amplitude": {
                "failed@0.5": 54, "passed@0.25": 1152, "passed@0.5": 1026,
            },
            "maximum_cancel_increment_by_amplitude": {
                "0.25": 0.23606572488943792, "0.5": 0.3506501714388529,
            },
            "cancellation_failure_static_match_count": 54,
        }
        self.assertTrue(d1._source_applicability(active, self.cfg))
        active["cancellation_event_counts_by_amplitude"] = {
            "failed@0.25": 1, "failed@0.5": 53,
            "passed@0.25": 1151, "passed@0.5": 1026,
        }
        self.assertFalse(d1._source_applicability(active, self.cfg))

    def test_sentinel_spec_has_fresh_identity_and_no_source_outcome(self):
        replay = d1._replay_config(self.s23r1_cfg, self.cfg)
        failure = [{
            "experiment_id": "source_old", "pair_id": "p5_q1",
            "history_member": "plus_first", "sequence_index": 6,
            "failure_class": d1.ALLOWED_FAILURE,
        }]
        specs = [{
            "experiment_id": "source_old", "pair_id": "p5_q1",
            "history_member": "plus_first", "s24_sequence_index": 6,
            "restart_snapshot_dir": "/server/source/snapshot", "horizon_steps": 35,
            "source_result_available_to_controller": False,
        }]
        rows = d1._sentinel_rows(failure, specs, replay, self.cfg, "a" * 64)
        self.assertEqual(len(rows), 1)
        spec = rows[0]["sentinel_spec"]
        self.assertEqual(spec["stage"], "Stage4.2R3c3T13S24D2")
        self.assertNotEqual(spec["experiment_id"], "source_old")
        self.assertEqual(spec["restart_snapshot_dir"], "/server/source/snapshot")
        self.assertFalse(spec["source_result_available_to_controller"])
        self.assertNotIn("source_failure_class", spec)
        self.assertNotIn("source_s24_experiment_id", spec)
        self.assertEqual(
            max(abs(v) for values in spec["s24_requested_action_by_task_step"].values() for v in values),
            0.225,
        )

    def test_design_preserves_zero_tsc_and_sentinel_only_scope(self):
        text = DESIGN.read_text(encoding="utf-8")
        self.assertIn("zero-new-TSC", text)
        self.assertIn("cannot authorize a full identification campaign directly", text)
        self.assertIn("0.24", text)
        self.assertFalse(self.cfg["scientific_scope"]["pass_authorizes_full_campaign"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_launchers_use_server_virtualenv_and_zero_tsc_path(self):
        common = (ROOT / "run_stage4_2r3c3t13s24d1_common.sh").read_text(encoding="utf-8")
        shell_common = (ROOT / "scripts" / "stage4_2r3c3t13s24d1_shell_common.sh").read_text(encoding="utf-8")
        offline = (ROOT / "run_stage4_2r3c3t13s24d1_offline.sh").read_text(encoding="utf-8")
        self.assertIn("zero plant/controller/Ray/gotsc/TSC execution", common)
        self.assertIn("stage4_2r3c3t13s24d1_contracted_amplitude_preflight.py", common)
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell_common)
        self.assertNotIn("ray start", common.lower())
        self.assertIn("run_stage4_2r3c3t13s24d1_common.sh", offline)


if __name__ == "__main__":
    unittest.main()
