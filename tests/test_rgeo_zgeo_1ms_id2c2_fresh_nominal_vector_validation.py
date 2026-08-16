import copy
import json
import math
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation as stage
from scripts import rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_independent as independent


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2c2_fresh_nominal_vector_validation.json"


def _state(r=0.0, z=0.0, ip=1000.0, label="x"):
    return {
        "time_ms": 1100,
        "r_geo_m": r,
        "z_geo_m": z,
        "r_mid_m": 0.8,
        "ip_a": ip,
        "actual_current_decimal_a_tsc": ["0"] * 14,
        "wire_current_a": [0.0] * 48,
        "artifact_sha256": {name: f"{label}:{name}" for name in ("inputa", "geqdsk", "coil_currents.csv", "wire_currents.csv", "sprsina")},
    }


def _synthetic_rows(config):
    vectors = {
        ("p04", "plus"): (0.00005, 0.0),
        ("p04", "minus"): (-0.00005, 0.0),
        ("p07", "plus"): (0.000025, 0.0000433012701892),
        ("p07", "minus"): (-0.000025, -0.0000433012701892),
        ("p09_half_exact_center", "plus"): (-0.000025, 0.0000433012701892),
        ("p09_half_exact_center", "minus"): (0.000025, -0.0000433012701892),
    }
    rows = []
    for cell in config["cells_in_order"]:
        for replay in range(2):
            states = [_state(label=f"{cell['cell_id']}:{index}") for index in range(33)]
            for index, state_row in enumerate(states):
                state_row["time_ms"] = 1100 + index
            if cell["kind"] == "q0":
                states[-1]["r_geo_m"], states[-1]["z_geo_m"] = 0.03, 0.04
            elif cell["kind"] == "full_nominal":
                states[-1]["r_geo_m"], states[-1]["z_geo_m"] = 0.018, 0.024
            elif cell["kind"] == "residual":
                x, y = vectors[(cell["direction_id"], cell["sign"])]
                for index in range(17, 33):
                    scale = 1.0 if index == 17 else 0.2
                    states[index]["r_geo_m"] = x * scale
                    states[index]["z_geo_m"] = y * scale
                    states[index]["ip_a"] = 1010.0 if index == 17 else 1001.0
            rows.append({
                "rollout_id": f"{cell['cell_id']}_r{replay}",
                "pair_id": cell["cell_id"],
                "cell_id": cell["cell_id"],
                "cell_kind": cell["kind"],
                "replay_index": replay,
                "direction_id": cell.get("direction_id"),
                "sign": cell.get("sign"),
                "passed": True,
                "reasons": [],
                "states": states,
                "actions": [{"issue_step": index} for index in range(32)],
            })
    return rows


class Id2C2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.cfg, cls.source, cls.targets, cls.id2c1 = stage.load(CONFIG)

    def test_frozen_identity_budget_and_roles(self):
        self.assertEqual(stage.sha256(CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(self.config["maximum_rollouts"], 18)
        self.assertEqual(self.config["maximum_advance_attempts"], 576)
        self.assertEqual(self.config["model_fit_use"], "forbidden")
        self.assertEqual(self.config["holdout_records_read"], 0)

    def test_streams_are_fixed_pairs_without_selection(self):
        rows = stage.campaign_streams(self.config, self.cfg, self.targets, self.id2c1)
        self.assertEqual(len(rows), 18)
        self.assertEqual([row["replay_index"] for row in rows], [0, 1] * 9)
        self.assertTrue(all(len(row["targets"]) == 32 and len(row["actions"]) == 32 for row in rows))
        for left, right in zip(rows[::2], rows[1::2]):
            self.assertEqual(left["pair_id"], right["pair_id"])
            self.assertEqual(left["actions"], right["actions"])
            self.assertEqual(left["targets"], right["targets"])
        nominal = rows[2]
        self.assertEqual(nominal["p03_minus_increment_issues"], list(range(1, 32)))
        self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in nominal["actions"]), 0.3)

    def test_phase_b_has_exact_one_issue_and_return(self):
        rows = stage.campaign_streams(self.config, self.cfg, self.targets, self.id2c1)
        baseline = next(row for row in rows if row["cell_id"] == "selected_nominal_probe_baseline")
        for row in rows:
            if row["cell_kind"] != "residual":
                continue
            self.assertEqual(row["targets"][:16], baseline["targets"][:16])
            self.assertNotEqual(row["targets"][16], baseline["targets"][16])
            self.assertEqual(row["targets"][17:], baseline["targets"][17:])
            self.assertLessEqual(max(action["maximum_issued_delta_a"] for action in row["actions"]), 0.3)

    def test_synthetic_validation_passes_all_gates(self):
        metrics = stage.validation_metrics(_synthetic_rows(self.config), self.config)
        self.assertIsNotNone(metrics)
        self.assertTrue(all(metrics["gate_passes"].values()), metrics["gate_passes"])
        self.assertEqual(len(metrics["repeatability"]), 9)
        self.assertEqual([row["peak_rz_rank"] for row in metrics["replay_metrics"]], [2, 2])
        self.assertLessEqual(max(row["circular_maximum_angular_gap_deg"] for row in metrics["replay_metrics"]), 150.0)

    def test_tail_gate_is_not_hidden_by_signal(self):
        rows = _synthetic_rows(self.config)
        target = next(row for row in rows if row["cell_id"] == "selected_nominal_p04_plus" and row["replay_index"] == 0)
        target["states"][-1]["r_geo_m"] = 0.00004
        metrics = stage.validation_metrics(rows, self.config)
        self.assertTrue(metrics["gate_passes"]["residual_signal_and_ip"])
        self.assertFalse(metrics["gate_passes"]["residual_tail"])

    def test_config_mutation_fails_closed(self):
        mutated = copy.deepcopy(self.config)
        mutated["scientific_gates"]["maximum_circular_angular_gap_deg"] = 180.0
        with self.assertRaises(stage.InputIntegrityError):
            stage._exact_stage(mutated)

    def test_offline_is_zero_plant_and_independent_order_is_fixed(self):
        result = stage.offline(CONFIG, "test")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"], result["plant_advance_gotsc_calls"]), (0, 0, 0))
        order = independent._campaign_order(self.config)
        self.assertEqual(order["fresh_q0_baseline_r0"], 0)
        self.assertEqual(order["fresh_q0_baseline_r1"], 1)
        self.assertEqual(order["selected_nominal_p09_half_exact_center_minus_r1"], 17)
        self.assertNotEqual(independent.SCHEMA, stage.SCHEMA)


if __name__ == "__main__":
    unittest.main()
