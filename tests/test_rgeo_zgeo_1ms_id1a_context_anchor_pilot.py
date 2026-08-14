import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot import (
    CONFIG_SHA256,
    load,
    rollout_specs,
    route_for,
    scientific_metrics,
    targets_and_streams,
)
from scripts.rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent import (
    _metrics as independent_metrics,
    _numeric_max_difference,
)
from tsc_rzip_rllib.core.runner import TSCConfig


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id1a_context_anchor_pilot.json"


def loaded():
    with patch.object(TSCConfig, "validate", lambda self: None):
        return load(CONFIG)


def compact_source():
    row = json.loads(
        (
            ROOT
            / "docs/codex/audits/rgeo_zgeo_1ms_id0t1_result_20260814_18788cf4/baseline_q0_r0.json"
        ).read_text(encoding="utf-8")
    )["states"][0]
    return {
        "currents_a_tsc": [float(value) for value in row["actual_current_decimal_a_tsc"]],
        "active_command_decimal_a_tsc": row["active_command_decimal_a_tsc"],
    }


def synthetic_rows(stage):
    rows = []
    directions = {
        ("p03", "plus"): (0.00002, 0.0),
        ("p03", "minus"): (-0.00002, 0.0),
        ("p07", "plus"): (0.0, 0.00002),
        ("p07", "minus"): (0.0, -0.00002),
    }
    context_offset = {
        "q0_baseline": (0.0, 0.0, 0.0),
        "early_q0": (0.0, 0.0, 0.0),
        "late_q0": (0.0, 0.0, 0.0),
        "history_p04_plus": (0.00005, 0.0, 5.0),
        "history_p04_minus": (-0.00005, 0.0, -5.0),
        "anchor_p03_minus": (0.0002, 0.0, 10.0),
        "anchor_p07_plus": (0.0, 0.0002, -10.0),
    }
    response_extra = {
        "history_p04_plus": 0.000003,
        "history_p04_minus": -0.000003,
        "anchor_p03_minus": 0.000006,
        "anchor_p07_plus": -0.000006,
    }
    for spec in rollout_specs(stage):
        offset = context_offset[spec["context_id"]]
        states = []
        for index in range(25):
            state = {
                "r_geo_m": 0.7 - 0.0005 * index + offset[0],
                "z_geo_m": 0.03 + 0.0007 * index + offset[1],
                "ip_a": 31000.0 - 10.0 * index + offset[2],
            }
            if not spec["is_context_baseline"] and index >= spec["pulse_issue_step"] + 1:
                dr, dz = directions[(spec["direction_id"], spec["sign"])]
                if spec["direction_id"] == "p03":
                    dr += response_extra.get(spec["context_id"], 0.0)
                state["r_geo_m"] += dr
                state["z_geo_m"] += dz
                state["ip_a"] += 1.0
            states.append(state)
        rows.append({**spec, "states": states})
    return rows


class Id1AContextAnchorPilotTest(unittest.TestCase):
    def test_frozen_matrix_and_exact_streams(self):
        stage, cfg, evidence = loaded()
        self.assertEqual(CONFIG_SHA256, "883945f8a15ba1d9aabe037fde6e51ba420cb7a59ba792df1064611b3ba196bf")
        specs = rollout_specs(stage)
        streams = targets_and_streams(stage, cfg, evidence, compact_source())
        self.assertEqual(len(specs), 32)
        self.assertEqual(sum(len(row["actions"]) for row in streams), 768)
        self.assertEqual(sum(row["is_context_baseline"] for row in specs), 6)
        for row in streams:
            self.assertLessEqual(max(float(action["maximum_issued_delta_a"]) for action in row["actions"]), 0.3)
            self.assertEqual([action["effect_state_index"] for action in row["actions"]], list(range(1, 25)))
            if row["prefix_id"] != "q0":
                self.assertEqual(
                    row["actions"][row["pulse_issue_step"] - 1]["expected_card15_fields"],
                    row["actions"][0]["expected_card15_fields"],
                )

    def test_matched_baseline_metrics_pass_synthetic_contract(self):
        stage, _, _ = loaded()
        rows = synthetic_rows(stage)
        metrics = scientific_metrics(rows, stage)
        self.assertTrue(metrics["signal_passed"])
        self.assertTrue(metrics["ip_passed"])
        self.assertTrue(metrics["vector_geometry_passed"])
        self.assertTrue(metrics["history_contrast_passed"])
        self.assertTrue(metrics["anchor_contrast_passed"])
        self.assertLessEqual(_numeric_max_difference(metrics, independent_metrics(rows, stage)), 1e-12)

    def test_route_precedence(self):
        stage, _, _ = loaded()
        metrics = scientific_metrics(synthetic_rows(stage), stage)
        self.assertEqual(route_for(stage, False, False, False, None), stage["routes"]["execution_or_interface_fail"])
        self.assertEqual(route_for(stage, True, False, False, None), stage["routes"]["raw_integrity_fail"])
        self.assertEqual(route_for(stage, True, True, False, None), stage["routes"]["repeatability_fail"])
        broken = copy.deepcopy(metrics)
        broken["history_contrast_passed"] = False
        self.assertEqual(route_for(stage, True, True, True, broken), stage["routes"]["history_contrast_fail"])
        broken = copy.deepcopy(metrics)
        broken["anchor_contrast_passed"] = False
        self.assertEqual(route_for(stage, True, True, True, broken), stage["routes"]["anchor_contrast_fail"])
        self.assertEqual(route_for(stage, True, True, True, metrics), stage["routes"]["pass"])

    def test_launcher_runs_independent_after_complete_primary(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id1a_context_anchor_pilot.sh").read_text(encoding="utf-8")
        self.assertIn('row.get("execution_passed") and row.get("raw_integrity_passed")', text)
        self.assertIn("rgeo_zgeo_1ms_id1a_context_anchor_pilot_independent.py", text)
        self.assertIn('exit "$PRIMARY_RC"', text)


if __name__ == "__main__":
    unittest.main()
