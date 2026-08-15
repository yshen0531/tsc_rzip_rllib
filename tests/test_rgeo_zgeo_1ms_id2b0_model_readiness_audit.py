import copy
import json
from pathlib import Path
import unittest

import numpy as np

from scripts.rgeo_zgeo_1ms_id2b0_model_readiness_audit import (
    CONFIG_SHA256,
    analyze_rows,
    load_config,
    output_response_hankel,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id2b0_model_readiness_audit.json"
LAUNCHER = ROOT / "run_rgeo_zgeo_1ms_id2b0_model_readiness_audit.sh"
PRIMARY = ROOT / "scripts/rgeo_zgeo_1ms_id2b0_model_readiness_audit.py"
INDEPENDENT = ROOT / "scripts/rgeo_zgeo_1ms_id2b0_model_readiness_independent.py"


def synthetic_rows() -> tuple[list[dict], dict, dict]:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    stage = {
        "directions": ["p01", "p09_half_exact_center"],
        "durations_issues": [1, 2, 4],
        "identifiability_gates": {
            "minimum_peak_rz_response_norm_m_per_context_direction_sign": 0.00001,
        },
    }
    rows = []
    contexts = config["contexts"]
    for context_index, context in enumerate(contexts):
        def states(response_scale: float = 0.0) -> list[dict]:
            result = []
            for index in range(33):
                prefix_shift = context_index * 1e-5 * min(index, 10)
                response = response_scale * max(0, index - 10)
                result.append(
                    {
                        "time_ms": 1100 + index,
                        "r_geo_m": 0.70 + index * 1e-4 + prefix_shift + response,
                        "z_geo_m": 0.03 + index * 2e-4 - prefix_shift - 0.5 * response,
                        "ip_a": 31000.0 - index + context_index + response * 1e5,
                        "actual_current_decimal_a_tsc": [str(-80.0 + context_index * 0.01 * min(index, 10))] * 14,
                    }
                )
            return result

        actions = [
            {
                "issue_step": index,
                "expected_card15_fields": [f"{context_index + index * 0.001:.3E}"] * 14,
                "target_current_a_tsc": [-80.0 + context_index * 0.01 * min(index, 10)] * 14,
            }
            for index in range(32)
        ]
        rows.append(
            {
                "rollout_id": f"{context}_baseline_r0",
                "context_id": context,
                "prefix_id": context,
                "is_context_baseline": True,
                "direction_id": None,
                "sign": None,
                "duration_issues": 0,
                "repeat_index": 0,
                "states": states(),
                "actions": copy.deepcopy(actions),
            }
        )
        for direction_index, direction in enumerate(stage["directions"]):
            for sign in ("plus", "minus"):
                signed = 1.0 if sign == "plus" else -1.0
                for duration in stage["durations_issues"]:
                    scale = signed * (direction_index + 1) * duration * (context_index + 1) * 1e-6
                    rows.append(
                        {
                            "rollout_id": f"{context}_{direction}_{sign}_d{duration}_r0",
                            "context_id": context,
                            "prefix_id": context,
                            "is_context_baseline": False,
                            "direction_id": direction,
                            "sign": sign,
                            "duration_issues": duration,
                            "repeat_index": 0,
                            "states": states(scale),
                            "actions": copy.deepcopy(actions),
                        }
                    )
        critical = next(
            row for row in rows
            if row["context_id"] == context
            and row["direction_id"] == "p09_half_exact_center"
            and row["sign"] == "minus"
            and row["duration_issues"] == 4
            and row["repeat_index"] == 0
        )
        replay = copy.deepcopy(critical)
        replay["rollout_id"] = f"{context}_p09_half_exact_center_minus_d4_r1"
        replay["repeat_index"] = 1
        rows.append(replay)
    return rows, config, stage


class Id2B0ModelReadinessAuditTest(unittest.TestCase):
    def test_frozen_config_hash_and_zero_execution_contract(self):
        self.assertEqual(sha256_file(CONFIG), CONFIG_SHA256)
        config = load_config(ROOT, CONFIG)
        self.assertEqual(config["plant_advances"], 0)
        self.assertFalse(config["model_fit_or_training"])
        self.assertEqual(config["holdout_records_read"], 0)
        self.assertEqual(
            config["available_takeover_history"]["maximum_true_explicit_action_lag_at_origin"],
            10,
        )

    def test_response_hankel_reports_descriptive_energy_ranks(self):
        time = np.arange(22, dtype=float)
        responses = [
            np.stack((1e-5 * time, -2e-5 * time, 0.1 * time), axis=1),
            np.stack((2e-5 * time, 1e-5 * time, -0.2 * time), axis=1),
        ]
        result = output_response_hankel(
            responses,
            {"r_geo_m": 0.001, "z_geo_m": 0.001, "ip_a": 100.0},
            6,
            [0.95, 0.99, 0.999],
        )
        self.assertEqual(result["rows"], 18)
        self.assertEqual(result["columns"], 34)
        self.assertTrue(result["descriptive_only_not_plant_order"])
        self.assertGreaterEqual(result["numerical_rank"], 1)

    def test_matched_baseline_analysis_uses_39_unique_cells(self):
        rows, config, stage = synthetic_rows()
        result = analyze_rows(rows, config, stage)
        self.assertEqual(result["counts"]["whole_trajectory_records"], 42)
        self.assertEqual(result["counts"]["unique_whole_trajectory_cells"], 39)
        self.assertEqual(result["counts"]["unique_action_cells"], 36)
        self.assertEqual(result["counts"]["exact_critical_replays"], 3)
        self.assertEqual(result["exact_causal_collisions"], [])
        self.assertTrue(all(result["sibling_prefix_exact"].values()))
        self.assertEqual(len(result["per_arm"]), 36)
        self.assertEqual(len(result["signed_even_odd"]), 18)

    def test_exact_prefix_with_different_response_is_a_collision(self):
        rows, config, stage = synthetic_rows()
        left = config["contexts"][0]
        right = config["contexts"][1]
        left_rows = [row for row in rows if row["context_id"] == left]
        right_rows = [row for row in rows if row["context_id"] == right]
        for right_row in right_rows:
            matching = next(
                row for row in left_rows
                if row["is_context_baseline"] == right_row["is_context_baseline"]
                and row["direction_id"] == right_row["direction_id"]
                and row["sign"] == right_row["sign"]
                and row["duration_issues"] == right_row["duration_issues"]
                and row["repeat_index"] == right_row["repeat_index"]
            )
            right_row["states"][:11] = copy.deepcopy(matching["states"][:11])
            right_row["actions"][:10] = copy.deepcopy(matching["actions"][:10])
        result = analyze_rows(rows, config, stage)
        self.assertTrue(any(f"{left}:{right}" in value for value in result["exact_causal_collisions"]))

    def test_launcher_and_auditors_do_not_run_tsc_or_fit_models(self):
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in (LAUNCHER, PRIMARY, INDEPENDENT)
        )
        self.assertNotIn("TSCStepRunner(", combined)
        self.assertNotIn("step_current_a(", combined)
        self.assertNotIn("gotsc(", combined)
        self.assertNotIn("optimizer.step(", combined)
        self.assertNotIn(".backward(", combined)
        self.assertIn("model_fit_or_training", CONFIG.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
