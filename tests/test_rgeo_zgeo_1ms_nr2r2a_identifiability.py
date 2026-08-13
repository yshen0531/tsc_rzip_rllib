from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


PRIMARY = _module("nr2r2a_primary", "scripts/rgeo_zgeo_1ms_nr2r2a_identifiability.py")
INDEPENDENT = _module("nr2r2a_independent", "scripts/rgeo_zgeo_1ms_nr2r2a_independent.py")


class NR2R2AIdentifiabilityTests(unittest.TestCase):
    def test_unpadded_lag_matrix_shape_rank_and_no_cross_trajectory_rows(self) -> None:
        sequence = np.zeros((2, 16, 14), dtype=float)
        sequence[0, 0, 0] = 0.3
        sequence[1, 1, 1] = 0.3
        result = PRIMARY._matrix_table(sequence, [1, 2], 0.3)
        self.assertEqual(result["by_lag"]["1"]["rows"], 32)
        self.assertEqual(result["by_lag"]["2"]["rows"], 30)
        self.assertEqual(result["by_lag"]["2"]["columns"], 28)
        self.assertLess(result["by_lag"]["2"]["rank"], 28)

    def test_q0_offset_differs_from_issued_increment(self) -> None:
        record = {
            "spec": {"split": "development", "schedule": [["zero", None]] * 16},
            "actions": [],
        }
        center = [0.0] * 14
        previous = center[:]
        for step in range(16):
            target = center[:]
            if step >= 1:
                target[0] = 0.3
            increment = [target[index] - previous[index] for index in range(14)]
            record["actions"].append(
                {"target": {"current_a_tsc": target}, "command_delta_decimal_a_tsc": [str(x) for x in increment]}
            )
            previous = target
        config = {"allowed_splits": ["development"], "lag_lengths": [1], "matrix_scale_a": 0.3}
        result = PRIMARY._action_geometry([record], config)
        self.assertEqual(result["maximum_absolute_q0_offset_a"], 0.3)
        self.assertEqual(result["maximum_absolute_issued_increment_a"], 0.3)
        self.assertEqual(record["_audit_issued_increment"][2][0], 0.0)
        self.assertEqual(record["_audit_q0_offset"][2][0], 0.3)

    def test_independent_comparator_rejects_nested_numeric_mismatch(self) -> None:
        with self.assertRaisesRegex(AssertionError, "root.a\[1\]"):
            INDEPENDENT.same({"a": [1.0, 2.0]}, {"a": [1.0, 2.1]}, 1e-12, 1e-12)

    def test_primary_output_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            target = Path(folder) / "result.json"
            PRIMARY._write_new(target, {"passed": True})
            self.assertEqual(json.loads(target.read_text())["passed"], True)
            with self.assertRaises(FileExistsError):
                PRIMARY._write_new(target, {"passed": False})

    def test_source_representation_facts_are_authenticated(self) -> None:
        facts = PRIMARY._source_representation()
        self.assertEqual(facts["arx_history_steps"], 8)
        self.assertTrue(facts["short_history_repeats_first_frame"])
        self.assertTrue(facts["absolute_step_over_16_feature"])
        self.assertFalse(facts["explicit_stable_low_order_passive_innovation_state"])
        self.assertEqual(facts, INDEPENDENT.source_result())


if __name__ == "__main__":
    unittest.main()
