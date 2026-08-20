from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import unittest
import uuid

from scripts import rgeo_zgeo_1ms_id2z24_centered_coallocation_preflight as p
from scripts import rgeo_zgeo_1ms_id2z24_centered_coallocation_independent as ia


ROOT = Path(__file__).resolve().parents[1]


class ID2Z24PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage = json.loads(p.CONFIG.read_text(encoding="utf-8"))
        cls.result = p.execute(p.CONFIG, "TEST_REVISION")

    def test_zero_tsc_identity_and_budget(self) -> None:
        self.assertEqual(self.stage["stage"], "ID-2Z24R2")
        self.assertEqual(self.stage["maximum_tsc_calls"], 0)
        self.assertEqual(self.stage["maximum_plant_advances"], 0)
        self.assertEqual(self.result["tsc_calls"], 0)
        self.assertEqual(self.result["plant_advances"], 0)
        self.assertEqual(self.result["models_fit_or_updated"], 0)
        self.assertEqual(self.result["prospective_budget"]["rollouts"], 15)
        self.assertEqual(self.result["prospective_budget"]["advance_attempts"], 975)

    def test_attribution_reproduces_omitted_f_dominance(self) -> None:
        row = self.result["attribution"]
        self.assertTrue(row["passed"], row)
        self.assertAlmostEqual(row["replacement_common_action_energy_fraction"],
                               0.68411398, places=6)
        self.assertAlmostEqual(row["common_rz_response_energy_fraction"]["24"],
                               0.91411202, places=6)
        self.assertAlmostEqual(row["common_rz_response_energy_fraction"]["32"],
                               0.89781331, places=6)
        self.assertGreater(row["p05_odd_cross_phase_cosine"]["4"], .9999)
        self.assertGreater(row["p05_odd_cross_phase_cosine"]["8"], .9999)

    def test_largest_exact_share_is_selected_without_search(self) -> None:
        self.assertTrue(self.result["passed"], self.result.get("failures"))
        self.assertEqual(self.result["selected_nominal_share"], "0.50")
        self.assertEqual(self.result["route"], self.stage["routes"]["pass"])
        self.assertTrue(all(row["passed"] for row in
                            self.result["selected_construction"]["local_vertex_checks"]))

    def test_all_signed_streams_close_exactly_and_respect_current(self) -> None:
        rows = self.result["selected_construction"]["prospective_static_streams"]
        self.assertEqual(len(rows), 13)
        for row in rows:
            self.assertTrue(row["prefix_exact"], row)
            self.assertTrue(row["closure_exact"], row)
            self.assertLessEqual(row["maximum_issued_delta_a"], .3000000001)
            self.assertGreaterEqual(row["minimum_absolute_current_headroom_a"], 0.0)
            if row["rollout_id"] != "baseline_center":
                self.assertEqual(row["return_bridge_issue_count"], 8)

    def test_combined_target_semantics_and_d0_boundary(self) -> None:
        action = self.stage["action_semantics"]
        self.assertTrue(action["construct_combined_target_then_quantize_once"])
        self.assertFalse(action["separately_quantize_then_add"])
        self.assertFalse(action["legacy_runner_clipping_may_be_relied_on"])
        data = self.stage["prospective_data_contract"]
        self.assertFalse(data["d0_requires_positive_span_or_capture"])
        self.assertEqual(data["replay_fit_weight"], 0)
        self.assertEqual(data["full_f_diagnostic_fit_weight"], 0)

    def test_contract_mutations_fail_closed(self) -> None:
        original = copy.deepcopy(self.stage)
        mutations = (
            lambda value: value.update(maximum_tsc_calls=1),
            lambda value: value.update(nominal_share_candidates_descending=["0.60"]),
            lambda value: value["residual_axes"][0].update(scale="0.60"),
            lambda value: value["action_semantics"].update(
                legacy_runner_clipping_may_be_relied_on=True),
            lambda value: value.update(maximum_prospective_advance_attempts=976),
        )
        for mutation in mutations:
            value = copy.deepcopy(original)
            mutation(value)
            with self.assertRaises(Exception):
                p._require(value)

    def test_independent_recomputation_matches_primary(self) -> None:
        temp = ROOT / ".codex_tmp" / f"id2z24_test_{uuid.uuid4().hex}"
        temp.mkdir(parents=True)
        try:
            primary = temp / "result.json"
            primary.write_text(json.dumps(self.result), encoding="utf-8")
            audit = ia.execute(primary, "TEST_REVISION")
            self.assertTrue(audit["audit_passed"], audit.get("failures"))
            self.assertEqual(audit["independently_selected_nominal_share"], "0.50")
            self.assertEqual(audit["independently_passing_nominal_shares"],
                             ["0.50", "0.45", "0.40", "0.35", "0.30", "0.25"])
        finally:
            shutil.rmtree(temp)


if __name__ == "__main__":
    unittest.main()
