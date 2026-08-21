from __future__ import annotations

import copy
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from scripts import rgeo_zgeo_1ms_id2z34_event_set_model as m
from scripts import rgeo_zgeo_1ms_id2z34_event_set_model_independent as mi


ROOT = Path(__file__).resolve().parents[1]


class ID2Z34Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.evidence = m.load()

    def test_identity_and_roles_are_frozen(self) -> None:
        self.assertEqual(m._sha(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.stage["candidates"]["candidate_count"], 2)
        self.assertFalse(self.stage["candidates"]["hyperparameter_search"])
        self.assertEqual(len(self.stage["data_contract"]["prospective_fit_families"]), 8)
        self.assertEqual(len(self.stage["data_contract"]["zero_fit_families"]), 2)
        self.assertEqual(self.stage["data_contract"]["id2z32_fit_weight"], 0)
        self.assertEqual(self.stage["data_contract"]["calibration_or_holdout_reads"], 0)

    def test_event_rule_is_uniform_and_isolates_one_cell(self) -> None:
        value = m.fit(self.stage, self.evidence)
        events = value["payload"]["event_sets"]
        self.assertEqual([(row["axis_sign"], row["effect_age"]) for row in events],
                         [("q_r:minus", 13)])
        self.assertLessEqual(events[0]["full_width"][0], .00075)

    def test_smooth_candidate_fails_and_event_set_candidate_passes(self) -> None:
        value = m.execute(source_revision="test-revision")
        self.assertFalse(value["model_payload"]["candidate_a"]["passed"])
        self.assertTrue(value["model_payload"]["candidate_b"]["passed"])
        self.assertEqual(value["selected_candidate"], "candidate_b")
        self.assertTrue(value["passed"])
        self.assertEqual(value["route"], self.stage["routes"]["candidate_b_pass"])

    def test_no_tsc_or_qualification_read(self) -> None:
        value = m.execute(source_revision="test-revision")
        self.assertEqual(value["tsc_calls"], 0)
        self.assertEqual(value["plant_advances"], 0)
        self.assertEqual(value["calibration_or_holdout_reads"], 0)
        source = inspect.getsource(m)
        self.assertNotIn("TSCStepRunner", source)
        self.assertNotIn("gotsc", source.lower())

    def test_config_mutation_fails_closed(self) -> None:
        changed = copy.deepcopy(self.stage)
        changed["development_gates"]["candidate_b_maximum_event_r_full_width_m"] = 1.0
        with self.assertRaises(Exception):
            m._require(changed)

    def test_independent_recomputes_without_primary_execute(self) -> None:
        primary = m.execute(source_revision="test-revision")
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as directory:
            path = Path(directory) / "primary.json"
            path.write_text(json.dumps(primary), encoding="utf-8")
            audit = mi.audit(mi.CONFIG, path, "test-revision")
        self.assertTrue(audit["audit_passed"], audit)
        self.assertEqual(audit["recomputed_selected_candidate"], "candidate_b")
        self.assertNotIn("m.execute", inspect.getsource(mi.audit))

    def test_launcher_runs_primary_and_independent_without_resume(self) -> None:
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z34_event_set_model.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z34_SOURCE_REVISION", launcher)
        self.assertIn("ID2Z34_OUTPUT", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertIn("independent_audit.json", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
