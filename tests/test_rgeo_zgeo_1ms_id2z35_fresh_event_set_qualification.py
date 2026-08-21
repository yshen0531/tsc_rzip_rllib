from __future__ import annotations

import copy
import inspect
import unittest
from pathlib import Path

from scripts import rgeo_zgeo_1ms_id2z35_fresh_event_set_qualification as m


ROOT = Path(__file__).resolve().parents[1]


class ID2Z35Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage, cls.base, cls.cfg, cls.preflight, cls.tracked, cls.model = m.load()

    def test_identity_model_and_staged_roles_are_frozen(self) -> None:
        self.assertEqual(m._sha(m.CONFIG), m.CONFIG_SHA256)
        self.assertEqual(self.model["payload_sha256"],
                         self.stage["evidence"]["id2z34_result"]["required_payload_sha256"])
        self.assertEqual(self.stage["calibration_phase_issue"], 52)
        self.assertEqual(self.stage["blind_phase_issue"], 54)
        self.assertFalse(self.stage["qualification"]["model_refit_after_calibration"])
        self.assertTrue(self.stage["qualification"]["blind_open_only_after_calibration_pass"])

    def test_all_streams_are_exact_and_separated_before_tsc(self) -> None:
        streams = m.build_streams(self.stage, self.cfg, self.preflight, self.tracked)
        self.assertEqual(len(streams), 10)
        self.assertTrue(m.action_separation(streams)["passed"])
        checks = [m.z33.z32.z31.z30.validate_stream(row, self.cfg) for row in streams]
        self.assertTrue(all(row["passed"] for row in checks), checks)
        self.assertTrue(m.offline(m.CONFIG, "test-revision")["passed"])

    def _synthetic_rows(self, role: str):
        phase = int(self.stage[f"{role}_phase_issue"])
        prefix = "cal52" if role == "calibration" else "blind54"
        baseline = copy.deepcopy(self.stage_baseline)
        baseline.update({"family_id": "baseline_transition_center", "passed": True})
        rows = [baseline]
        for axis in self.stage["output_aligned_axis_ids"]:
            for sign in self.stage["initial_signs"]:
                row = copy.deepcopy(self.stage_baseline)
                row.update({"family_id": f"{prefix}__{axis}__{sign}_then_return",
                            "passed": True})
                center = self.model["point_centers"][f"{axis}:{sign}"]
                for age, values in enumerate(center, start=1):
                    for key, value in zip(m.KEYS, values):
                        row["states"][phase + age][key] = (
                            float(row["states"][phase + age][key]) + float(value))
                rows.append(row)
        return rows

    @property
    def stage_baseline(self):
        return m.z33.z32._read(
            ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id2z33_20260821_3892b0c1_v1/baseline_transition_center.json")

    def test_calibration_then_blind_metric_contract(self) -> None:
        calibration_rows = self._synthetic_rows("calibration")
        calibration = m.qualification_metrics(
            calibration_rows, self.stage, self.model, "calibration")
        self.assertTrue(calibration["passed"], calibration)
        blind_rows = self._synthetic_rows("blind")
        blind = m.qualification_metrics(
            blind_rows, self.stage, self.model, "blind",
            calibration["calibrated_non_event_half_width"])
        self.assertTrue(blind["passed"], blind)
        self.assertEqual(blind["all_cell_containment_fraction"], 1.0)

    def test_new_event_age_fails_calibration_without_relabelling(self) -> None:
        rows = self._synthetic_rows("calibration")
        target = next(row for row in rows if row["family_id"] == "cal52__q_r__minus_then_return")
        target["states"][52 + 11]["r_geo_m"] += .0002
        value = m.qualification_metrics(rows, self.stage, self.model, "calibration")
        self.assertFalse(value["passed"], value)
        self.assertEqual(self.stage["qualification"]["event_effect_age"], 13)

    def test_blind_execution_is_guarded_by_calibration(self) -> None:
        source = inspect.getsource(m.execute)
        self.assertIn("calibration[\"passed\"]", source)
        self.assertIn("if blind_opened", source)
        self.assertIn("streams[6:]", source)
        self.assertNotIn("model_payload.update", source)

    def test_launcher_runs_independent_and_forbids_resume(self) -> None:
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2z35_fresh_event_set_qualification.sh").read_text(
            encoding="utf-8")
        self.assertIn("ID2Z35_SOURCE_REVISION", launcher)
        self.assertIn("independent_raw_audit.json", launcher)
        self.assertIn("primary_rc=$?", launcher)
        self.assertNotIn("--resume", launcher)


if __name__ == "__main__":
    unittest.main()
