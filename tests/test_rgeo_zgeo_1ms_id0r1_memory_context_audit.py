import json
import tempfile
import unittest
from pathlib import Path

from scripts.rgeo_zgeo_1ms_id0r1_memory_context_audit import audit


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_id0r1_memory_context_audit.json"


class Id0R1MemoryContextAuditTest(unittest.TestCase):
    def test_frozen_audit_recomputes_expected_route(self):
        result = audit(ROOT, CONFIG)
        self.assertEqual(
            result["route"],
            "ONE_MS_ID0R1_STABLE_LATENT_MEMORY_AND_ID1A_CONTEXT_PILOT_REQUIRED",
        )
        self.assertEqual(result["counters"]["plant_advances"], 0)
        self.assertEqual(result["counters"]["models_fit_or_trained"], 0)
        self.assertEqual(result["counters"]["holdout_records_read"], 0)
        self.assertEqual(len(result["arm_metrics"]), 6)
        self.assertTrue(result["summary"]["late_response_is_nonmonotone"])
        self.assertFalse(result["summary"]["position_time_history_factorization_supported"])
        self.assertLess(result["summary"]["maximum_terminal_rz_norm_mm"], 0.05)
        self.assertGreater(result["summary"]["maximum_late_window_rz_norm_mm"], 0.04)

    def test_hash_mismatch_fails_closed(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["records"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence hash mismatch"):
                audit(ROOT, path)

    def test_model_or_holdout_use_fails_closed(self):
        for field, value in (("model_fit_or_training", True), ("holdout_records_read", 1)):
            config = json.loads(CONFIG.read_text(encoding="utf-8"))
            config[field] = value
            with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
                path = Path(folder) / "bad.json"
                path.write_text(json.dumps(config), encoding="utf-8")
                with self.assertRaises(ValueError):
                    audit(ROOT, path)


if __name__ == "__main__":
    unittest.main()
