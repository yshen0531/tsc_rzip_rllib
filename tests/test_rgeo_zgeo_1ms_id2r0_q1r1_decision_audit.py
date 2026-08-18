import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


r0 = load("id2r0_primary", SCRIPTS / "rgeo_zgeo_1ms_id2r0_q1r1_decision_audit.py")


class ID2R0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.qstage, cls.data, cls.qresult = r0.load_stage()
        cls.baselines = r0.baseline_map(cls.data.cells)

    def test_frozen_zero_plant_identity(self):
        self.assertEqual(r0.sha256(r0.CONFIG), r0.CONFIG_SHA256)
        self.assertEqual((self.stage["new_tsc_calls"], self.stage["reset_calls"],
                          self.stage["plant_advances"]), (0, 0, 0))
        self.assertEqual(self.stage["diagnostic_refit"]["new_candidate_count"], 0)
        self.assertFalse(self.stage["diagnostic_refit"]["full_data_model_fit"])
        self.assertFalse(self.stage["diagnostic_refit"]["emit_model_payload"])
        self.assertTrue(all(self.stage["forbidden_sources"].values()))

    def test_q1_fail_and_evidence_identity_are_immutable(self):
        self.assertFalse(self.qresult["passed"])
        self.assertIsNone(self.qresult["selected_kind"])
        self.assertIsNone(self.qresult["model_payload_sha256"])
        self.assertEqual(self.qresult["route"],
                         "ONE_MS_ID2Q1R1_NO_ELIGIBLE_SHARED_LATENT_MODEL_REDESIGN")
        self.assertEqual(len(self.data.cells), 80)
        self.assertEqual(len({cell.group_id for cell in self.data.cells}), 16)

    def test_saved_array_family_mapping_is_explicit(self):
        ridge = next(row for row in self.qresult["candidate_results"]
                     if row["kind"] == "stable_shared_latent_ridge")
        q01 = next(row for row in ridge["folds"] if row["fold_id"] == "q01")
        q03 = next(row for row in ridge["folds"] if row["fold_id"] == "q03")
        self.assertEqual(sorted(q01["held_families"]), ["f01", "f05", "h01", "h05"])
        regrets = dict(zip(sorted(q01["held_families"]),
                           q01["metrics"]["family_ranking_regret"]))
        self.assertGreater(regrets["f01"], 0.6)
        self.assertGreater(regrets["f05"], 0.8)
        self.assertLess(regrets["h01"], 0.03)
        self.assertLess(regrets["h05"], 0.02)
        cosines = q03["metrics"]["peak_cosines"]
        family_order = sorted(q03["held_families"])
        mapped = {family: cosines[index * 4:(index + 1) * 4]
                  for index, family in enumerate(family_order)}
        self.assertTrue(all(value < 0 for value in mapped["f03"]))
        self.assertTrue(all(value > 0 for family in ("f07", "h03", "h07")
                            for value in mapped[family]))

    def test_fixed_prefix_is_96_dimensional_and_label_free(self):
        cell = next(cell for cell in self.data.cells
                    if cell.group_id == "f03" and cell.cell_kind == "probe")
        vector = r0.causal_prefix(cell, int(cell.probe_issue), self.stage)
        self.assertEqual(vector.shape, (96,))
        self.assertTrue(np.all(np.isfinite(vector)))
        original = vector.copy()
        saved = (cell.group_id, cell.direction, cell.sign)
        try:
            cell.group_id = "forbidden-family-label"
            cell.direction = "forbidden-direction-label"
            cell.sign = "forbidden-sign-label"
            self.assertTrue(np.array_equal(
                original, r0.causal_prefix(cell, int(cell.probe_issue), self.stage)))
        finally:
            cell.group_id, cell.direction, cell.sign = saved

    def test_exact_schedule_support_has_three_singletons(self):
        strata = {}
        for family, baseline in self.baselines.items():
            probe = next(cell for cell in self.data.cells
                         if cell.group_id == family and cell.cell_kind == "probe")
            signature = r0.schedule_stratum_signature(probe, baseline)
            strata.setdefault(signature, []).append(family)
        singletons = sorted(value[0] for value in strata.values() if len(value) == 1)
        self.assertEqual(singletons, ["f01", "f03", "f05"])

    def test_nearest_history_is_fixed_no_fit_and_abstains(self):
        result = r0.nearest_history_diagnostic(self.data, self.qstage, self.stage)
        self.assertEqual(result["probe_count"], 64)
        self.assertEqual(result["supported_probe_count"], 52)
        self.assertEqual(result["unsupported_probe_count"], 12)
        self.assertEqual(result["positive_supported_peak_directions"], 52)
        self.assertLess(result["supported_response_nrmse"], 0.75)
        self.assertLess(result["maximum_supported_family_action_ranking_regret"], 0.25)
        unsupported_families = sorted({cell_id.split("__", 1)[0]
                                       for cell_id in result["unsupported_cell_ids"]})
        self.assertEqual(unsupported_families, ["f01", "f03", "f05"])

    def test_geometry_distinguishes_peak_from_time_samples(self):
        rows = r0.measured_geometry(self.data)
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(not row["peak_geometry"]["positive_span_geometry"]
                            for row in rows))
        self.assertTrue(all(row["all_horizon_sample_geometry"]["positive_span_geometry"]
                            for row in rows))

    def test_route_precedence_selects_unreplayed_f03(self):
        family_rows = []
        for family in sorted(self.baselines):
            family_rows.append({
                "family_id": family,
                "probe_count": 4,
                "positive_peak_directions": 0 if family == "f03" else 4,
                "schedule_stratum_key": family,
            })
        local = {
            "support_fraction": 0.8125,
            "supported_probe_count": 52,
            "positive_supported_peak_directions": 52,
            "supported_response_nrmse": 0.04,
            "maximum_supported_family_action_ranking_regret": 0.02,
        }
        geometry = [{"all_horizon_sample_geometry": {"positive_span_geometry": True}}
                    for _ in range(16)]
        route, detail = r0.route_for(
            self.stage, family_rows, local, geometry,
            {family: 1 for family in self.baselines}, {})
        self.assertTrue(detail["critical_singleton_gate"])
        self.assertEqual(route,
                         "ONE_MS_ID2R0_CRITICAL_SINGLETON_F03_EXACT_REPLAY_REQUIRED")

    def test_launcher_contains_no_plant_entrypoint(self):
        text = (ROOT / "run_rgeo_zgeo_1ms_id2r0_q1r1_decision_audit.sh").read_text(
            encoding="utf-8")
        self.assertNotIn("gotsc", text.lower())
        self.assertNotIn("reset(", text.lower())
        self.assertNotIn("step_current", text.lower())


if __name__ == "__main__":
    unittest.main()
