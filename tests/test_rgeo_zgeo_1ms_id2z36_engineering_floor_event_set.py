import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import rgeo_zgeo_1ms_id2z36_engineering_floor_event_set as m
from scripts import rgeo_zgeo_1ms_id2z36_engineering_floor_event_set_independent as ind


class ID2Z36Tests(unittest.TestCase):
    def test_zero_use_and_single_candidate_contract(self):
        cfg = m.load_json(m.CONFIG)
        self.assertEqual(cfg["candidate_count"], 1)
        self.assertFalse(cfg["hyperparameter_search"])
        self.assertEqual(cfg["models_fit_or_updated"], 0)
        self.assertEqual(cfg["plant_advance_gotsc_calls"], 0)
        self.assertEqual(cfg["id2z35_fit_rows"], 0)

    def test_exact_engineering_floor_payload_and_independent(self):
        result = m.execute(m.CONFIG, "revision")
        self.assertTrue(result["passed"])
        event = result["model_payload"]["event_sets"][0]
        self.assertEqual(event["half_width"], [0.000375, 0.000075, 30.0])
        self.assertEqual(event["full_width"], [0.00075, 0.00015, 60.0])
        self.assertEqual(result["id2z35_fit_rows"], 0)
        with tempfile.TemporaryDirectory(dir=m.ROOT / ".codex_tmp") as td:
            p = Path(td) / "primary.json"
            p.write_text(json.dumps(result), encoding="utf-8")
            audit = ind.audit(m.CONFIG, p, "revision")
            self.assertTrue(audit["audit_passed"], audit["failures"])

    def test_identity_or_floor_mutation_fails(self):
        cfg = m.load_json(m.CONFIG)
        for mutation in ("floor", "fit"):
            changed = copy.deepcopy(cfg)
            if mutation == "floor": changed["engineering_half_width_floor"]["z_geo_m"] = 0.00008
            else: changed["id2z35_fit_rows"] = 1
            with patch.object(m, "load_json", side_effect=lambda path, c=changed: c if Path(path).resolve() == m.CONFIG.resolve() else json.loads(Path(path).read_text(encoding="utf-8"))):
                result = m.execute(m.CONFIG, "revision")
            self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
