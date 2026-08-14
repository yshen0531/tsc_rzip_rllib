import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import rgeo_zgeo_1ms_id0t1_long_tail as primary
from scripts import rgeo_zgeo_1ms_id0t1_long_tail_independent as independent
from tsc_rzip_rllib.core.runner import TSCConfig


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id0t1_long_tail.json"
Q0 = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_nr2r2c1a_result_20260814_778b454/q0_h32_r0.json"


class ID0T1LongTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        with patch.object(TSCConfig, "validate", lambda self: None):
            cls.cfg = TSCConfig.from_json(ROOT / cls.stage["base_tsc_config"])
        state = json.loads(Q0.read_text(encoding="utf-8"))["states"][0]
        cls.source = {"currents_a_tsc": state["actual_current_a_tsc"],
                      "active_command_decimal_a_tsc": state["active_command_decimal_a_tsc"]}

    def test_config_identity_and_budget(self):
        self.assertEqual(primary.sha256(CONFIG), primary.CONFIG_SHA256)
        primary._exact_stage(self.stage)
        self.assertEqual(len(primary.rollout_specs(self.stage)), 8)
        self.assertEqual(self.stage["maximum_advance_attempts"], 256)
        self.assertEqual(self.stage["completed_state_count"], 264)
        self.assertEqual(self.stage["completed_required_artifact_files"], 1320)

    def test_all_evidence_hashes_match(self):
        evidence = self.stage["evidence"]
        for key in ("id0_result_report", "id0_result", "id0_independent"):
            self.assertEqual(primary.sha256(ROOT / evidence[key]["path"]), evidence[key]["sha256"])
        for row in evidence["reference_records"]:
            self.assertEqual(primary.sha256(ROOT / row["path"]), row["sha256"])

    def test_action_stream_is_exact_finite_pulse_return(self):
        _, streams = primary.targets_and_stream(self.stage, self.cfg, self.source)
        self.assertEqual(len(streams), 8)
        for row in streams:
            self.assertEqual(len(row["targets"]), 32)
            self.assertEqual(len(row["actions"]), 32)
            self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in row["actions"]), 0.3)
            if row["pulse_issue_step"] is not None:
                self.assertEqual(row["pulse_issue_step"], 2)
                self.assertEqual(row["return_issue_step"], 3)
                self.assertAlmostEqual(row["actions"][2]["maximum_issued_delta_a"], 0.3)
                self.assertAlmostEqual(row["actions"][3]["maximum_issued_delta_a"], 0.3)
                self.assertTrue(all(action["maximum_issued_delta_a"] == 0 for action in row["actions"][4:]))

    def test_config_mutations_fail_closed(self):
        for key, value in (("horizon_steps", 33), ("maximum_advance_attempts", 257),
                           ("model_development_use", "allowed")):
            stage = copy.deepcopy(self.stage)
            stage[key] = value
            with self.assertRaises(primary.InputIntegrityError):
                primary._exact_stage(stage)

    def test_prefix_comparison_detects_action_and_state_changes(self):
        rows = self._synthetic_rows()
        refs = {}
        for row in self.stage["evidence"]["reference_records"]:
            refs[(ROOT / row["path"]).stem] = json.loads((ROOT / row["path"]).read_text(encoding="utf-8"))
        reference = refs["early_p03_plus_r0"]
        new = copy.deepcopy(reference)
        proxy = {"semantic_artifacts": self.stage["semantic_artifacts"],
                 "repeatability": {key: self.stage["prefix_match"][key] for key in ("geometry_m", "ip_a", "coil_a", "wire_a")}}
        self.assertTrue(primary.id0.compare_rows(new, reference, proxy)["passed"])
        new["states"][5]["r_geo_m"] += 2e-12
        self.assertFalse(primary.id0.compare_rows(new, reference, proxy)["passed"])
        self.assertEqual(len(rows), 8)

    def test_consumed_id0_prefixes_form_exact_reference_gate(self):
        references = {}
        for record in self.stage["evidence"]["reference_records"]:
            path = ROOT / record["path"]
            references[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        rows = []
        for spec in primary.rollout_specs(self.stage):
            key = "baseline_q0_r0" if spec["context_id"] == "baseline" else f"early_{spec['direction_id']}_{spec['sign']}_r0"
            row = copy.deepcopy(references[key])
            row.update(spec)
            rows.append(row)
        comparisons = primary.prefix_comparisons(rows, self.stage)
        self.assertEqual(len(comparisons), 16)
        self.assertTrue(all(row["passed"] for row in comparisons))
        source_command = independent._source_preissue_active_command(references)
        self.assertEqual(source_command, references["baseline_q0_r0"]["states"][0]["active_command_decimal_a_tsc"])
        self.assertEqual(len(source_command), 14)

    def test_independent_prefix_treats_raw_inputa_as_outgoing_action(self):
        reference_path = ROOT / next(
            row["path"] for row in self.stage["evidence"]["reference_records"]
            if Path(row["path"]).stem == "baseline_q0_r0"
        )
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
        raw_view = copy.deepcopy(reference)
        for state in raw_view["states"]:
            state["artifact_sha256"]["inputa"] = "outgoing-rewrite"
        self.assertTrue(independent._compare_prefix(raw_view, reference, self.stage)["passed"])
        raw_view["states"][4]["artifact_sha256"]["geqdsk"] = "changed-physical-state"
        self.assertFalse(independent._compare_prefix(raw_view, reference, self.stage)["passed"])

    def test_tail_metric_boundaries_and_independent_agreement(self):
        rows = self._synthetic_rows()
        first = primary.scientific_metrics(rows, self.stage)
        second = independent._metrics(rows, self.stage)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertTrue(first["tail_passed"])
        rows[2]["states"][32]["r_geo_m"] += 0.000051
        self.assertFalse(primary.scientific_metrics(rows, self.stage)["tail_passed"])

    def test_route_precedence_and_no_horizon_ladder(self):
        metrics = {"tail_passed": True}
        self.assertEqual(primary.route_for(self.stage, False, False, False, None), self.stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(primary.route_for(self.stage, True, False, False, None), self.stage["routes"]["raw_integrity_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, False, None), self.stage["routes"]["prefix_match_fail"])
        self.assertEqual(primary.route_for(self.stage, True, True, True, metrics), self.stage["routes"]["pass"])
        metrics["tail_passed"] = False
        self.assertEqual(primary.route_for(self.stage, True, True, True, metrics), self.stage["routes"]["tail_horizon_fail"])
        self.assertTrue(self.stage["scientific_gates"]["no_automatic_longer_horizon_after_fail"])

    def test_launcher_is_stage_specific(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id0t1_long_tail.sh").read_text(encoding="utf-8")
        self.assertIn("ID0T1_SOURCE_REVISION", text)
        self.assertIn("rgeo_zgeo_1ms_id0t1_long_tail_independent.py", text)
        self.assertNotIn("ID0_SOURCE_REVISION", text)

    def _synthetic_rows(self):
        rows = []
        vectors = {
            ("p03", "plus"): (1.0, 0.0), ("p03", "minus"): (-1.0, 0.0),
            ("p04", "plus"): (0.0, 1.0), ("p04", "minus"): (0.0, -1.0),
            ("p07", "plus"): (1.0, 1.0), ("p07", "minus"): (-1.0, -1.0),
        }
        for spec in primary.rollout_specs(self.stage):
            states = []
            for index in range(33):
                response = np.zeros(2)
                if spec["direction_id"] is not None and index >= 3:
                    decay = max(0.0, 1.0 - (index - 3) / 20.0)
                    response = np.asarray(vectors[(spec["direction_id"], spec["sign"])]) * 0.0001 * decay
                states.append({"time_ms": 1100 + index, "r_geo_m": 0.7 + response[0],
                               "z_geo_m": 0.03 + response[1], "r_mid_m": 0.79,
                               "ip_a": 31000.0, "actual_current_decimal_a_tsc": ["0"] * 14,
                               "wire_current_a": [0.0] * 48,
                               "artifact_sha256": {name: "x" for name in primary.id0.ARTIFACTS}})
            rows.append({**spec, "states": states, "actions": []})
        return rows


if __name__ == "__main__":
    unittest.main()
