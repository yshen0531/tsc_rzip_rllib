from __future__ import annotations

import copy
from decimal import Decimal
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from scripts import rgeo_zgeo_1ms_id2z28_event_value_model as m
from scripts import rgeo_zgeo_1ms_id2z28_event_value_model_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.evidence = m.load()
        cls.model = m.fit_kernel(cls.stage, cls.evidence)

    def test_identity_roles_and_data_are_frozen(self) -> None:
        self.assertEqual(m._sha(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["data_contract"]["models_fit_or_updated"], 1)
        self.assertEqual(self.stage["data_contract"]["calibration_or_holdout_reads"], 0)
        self.assertEqual(len(self.stage["data_contract"]["prospective_training_families"]), 5)
        self.assertEqual(len(self.stage["data_contract"]["internal_validation_families"]), 4)
        self.assertEqual(len(self.stage["data_contract"]["zero_fit_families"]), 2)

    def test_model_is_finite_causal_and_validation_is_whole_phase(self) -> None:
        self.assertEqual(self.model["class"], "finite_causal_signed_odd_fir")
        self.assertEqual(self.model["horizons"], list(range(1, 9)))
        self.assertEqual(len(self.model["causal_fir_kernel"]["q_r"]), 8)
        value = m.validate(self.stage, self.evidence, self.model)
        self.assertTrue(value["passed"], value)
        self.assertEqual(len(value["per_branch"]), 4)
        self.assertLessEqual(value["maximum_terminal_response_velocity_error_m_per_s"], .05)

    def test_nomination_is_exhaustive_deterministic_and_bounded(self) -> None:
        first = m.nominate(self.stage, self.evidence, self.model)
        second = m.nominate(self.stage, self.evidence, self.model)
        self.assertEqual(first, second)
        self.assertEqual(first["candidate_count"], 390625)
        self.assertEqual(len(first["selected_tokens"]), 8)
        self.assertEqual(len(first["opposite_tokens"]), 8)
        self.assertLess(first["relative_worst_score_improvement"], .15)

    def test_exact_selected_and_opposite_streams_close(self) -> None:
        nomination = m.nominate(self.stage, self.evidence, self.model)
        preflight = self.evidence["id2z26r1_preflight"]
        for phase in (32, 40):
            for tokens in (nomination["selected_tokens"], nomination["opposite_tokens"]):
                row = m.exact_stream(self.stage, preflight, tokens, phase)
                self.assertTrue(row["passed"], row)
                self.assertTrue(row["closure_exact"])
                self.assertEqual(len(row["card15_targets"]), 73)
                self.assertLessEqual(row["maximum_issued_delta_a"], .300000000001)
                self.assertGreaterEqual(row["minimum_absolute_current_headroom_a"], 0.0)

    def test_expected_route_is_model_pass_utility_fail(self) -> None:
        value = m.execute(source_revision="test-revision")
        self.assertTrue(value["model_validation_passed"], value)
        self.assertTrue(value["exact_action_preflight_passed"], value)
        self.assertFalse(value["control_utility_passed"])
        self.assertFalse(value["passed"])
        self.assertEqual(value["route"], self.stage["routes"]["utility_fail"])
        self.assertEqual(value["tsc_calls"], 0)
        self.assertEqual(value["plant_advances"], 0)

    def test_config_mutation_fails_closed(self) -> None:
        changed = copy.deepcopy(self.stage)
        changed["validation_gates"]["maximum_scaled_response_rmse"] = 99.0
        with self.assertRaises(Exception):
            m._require(changed)

    def test_independent_recomputes_without_primary_execute(self) -> None:
        primary = m.execute(source_revision="test-revision")
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as directory:
            path = Path(directory) / "primary.json"
            path.write_text(json.dumps(primary), encoding="utf-8")
            audit = mi.audit(mi.CONFIG, path, "test-revision")
        self.assertTrue(audit["audit_passed"], audit)
        self.assertEqual(audit["recomputed_route"], self.stage["routes"]["utility_fail"])
        source = inspect.getsource(mi.audit)
        self.assertNotIn("m.execute", source)

    def test_independent_card15_current_conversion_matches_frozen_interface(self) -> None:
        fields = ["1.000E+00 ", "-2.000E+00"]
        turns = [Decimal("10"), Decimal("20")]
        self.assertEqual(mi._currents(fields, turns).tolist(), [100.0, -100.0])

    def test_no_tsc_or_future_actual_access(self) -> None:
        source = inspect.getsource(m)
        self.assertNotIn("TSCStepRunner", source)
        self.assertNotIn("gotsc", source.lower())
        self.assertEqual(self.stage["model"]["future_actual_current"], "forbidden")
        self.assertEqual(self.stage["model"]["future_rzi"], "forbidden")

    def test_launcher_preserves_scientific_failure_and_runs_audit(self) -> None:
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z28_event_value_model.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z28_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z28_OUTPUT", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertIn("independent_audit.json", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
