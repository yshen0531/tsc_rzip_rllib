import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


m0 = load("id2m0_primary", SCRIPTS / "rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.py")
audit = load("id2m0_audit", SCRIPTS / "rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution_independent.py")


class ID2M0Tests(unittest.TestCase):
    def test_frozen_config_and_zero_plant_contract(self):
        stage = m0.load_stage()
        self.assertEqual(m0.sha256(m0.CONFIG), m0.CONFIG_SHA256)
        self.assertEqual((stage["new_tsc_calls"], stage["reset_calls"], stage["plant_advances"]), (0, 0, 0))
        self.assertEqual(stage["diagnostic_refit"]["new_candidates"], 0)
        self.assertFalse(stage["diagnostic_refit"]["model_artifact_authorized"])

    def test_forbidden_data_and_controller_outputs_remain_closed(self):
        stage = m0.load_stage()
        for key in ("id2i1_records_allowed", "id2j0_records_allowed", "id2c2_records_allowed",
                    "calibration_records_allowed", "holdout_records_allowed"):
            self.assertEqual(stage["data_use"][key], 0)
        for key in ("fixture_authorized", "expert_authorized", "controller_authorized", "mpc_authorized",
                    "authority_authorized", "recovery_authorized", "crossing_authorized",
                    "adaptation_authorized", "rl_authorized"):
            self.assertFalse(stage["data_use"][key])

    def test_numeric_comparison_rejects_categorical_change(self):
        self.assertEqual(m0._numeric_max_difference({"x": [1.0]}, {"x": [1.0]}), 0.0)
        with self.assertRaises(m0.IntegrityError):
            m0._numeric_max_difference({"x": "changed"}, {"x": "frozen"})

    def test_duplicate_key_requires_equal_truth_and_prediction(self):
        base = {"k": "same", "error_rzi": [1.0, 2.0, 3.0], "truth_delta_rzi": [4.0, 5.0, 6.0],
                "predicted_delta_rzi": [5.0, 7.0, 9.0]}
        p95, count = m0._deduplicated_metrics([base, dict(base)], "k")
        self.assertEqual(count, 1)
        self.assertEqual(p95, [1.0, 2.0, 3.0])
        changed = dict(base)
        changed["error_rzi"] = [2.0, 2.0, 3.0]
        with self.assertRaises(m0.IntegrityError):
            m0._deduplicated_metrics([base, changed], "k")

    def test_causal_keys_use_history_and_future_known_actions_only(self):
        cell = m0.l1.Cell("c", "h", "baseline", np.zeros((35, 3)), np.zeros((35, 14)),
                          np.zeros((34, 14)), None, None)
        first = m0.one_step_key(cell, 16)
        cell.states[16, 0] = 1.0
        self.assertNotEqual(first, m0.one_step_key(cell, 16))
        first = m0.segment_key(cell, 16, 17)
        cell.issued[17, 0] = 1.0
        self.assertNotEqual(first, m0.segment_key(cell, 16, 17))

    def test_event_labels_are_evaluator_only_causal_descriptions(self):
        issued = np.zeros((34, 14))
        issued[18:20, 0] = 0.3
        cell = m0.l1.Cell("c", "h", "baseline", np.zeros((35, 3)), np.zeros((35, 14)), issued, None, None)
        data = m0.l1.Dataset([], np.zeros(3), np.zeros(14), np.zeros((34, 14)), np.zeros((3, 14)), 3,
                             np.ones(3), np.ones(3))
        self.assertTrue(m0._event(cell, data, 18)["action_edge"])
        self.assertEqual(m0._event(cell, data, 19)["dwell_age_steps"], 2)
        self.assertTrue(m0._event(cell, data, 20)["return_edge"])
        self.assertTrue(m0._event(cell, data, 21)["delayed_tail"])

    def test_output_is_non_overwriting(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            target = Path(folder) / "value.json"
            m0.write_new(target, {"x": 1})
            with self.assertRaises(FileExistsError):
                m0.write_new(target, {"x": 2})

    def test_full_refit_reproduces_frozen_result_and_attribution(self):
        result, predictions = m0.compute(source_revision="test-revision")
        self.assertTrue(result["passed"])
        self.assertEqual(result["diagnostic_refits"], 4)
        self.assertEqual(result["model_payload_sha256"], None)
        self.assertLessEqual(result["maximum_aggregate_reproduction_difference"], 1e-12)
        self.assertEqual(result["attribution_checks"]["unique_one_step_keys_per_fold"], [106] * 4)
        self.assertEqual(len(predictions["rows"]), 720)
        self.assertTrue(result["evaluator_semantics"]["context_origin_rewrites_prior_context"])

    def test_separate_process_audit_recomputes_exact_outputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex_tmp") as folder:
            output = Path(folder) / "m0"
            result = m0.execute(m0.CONFIG, "test-revision", output)
            value = audit.audit(m0.CONFIG, "test-revision", output)
            self.assertTrue(result["passed"])
            self.assertTrue(value["audit_passed"])
            self.assertTrue(value["primary_result_exactly_recomputed"])
            self.assertTrue(value["primary_predictions_exactly_recomputed"])

    def test_launcher_has_no_plant_entrypoint(self):
        launcher = (ROOT / "run_rgeo_zgeo_1ms_id2m0_diagnostic_refit_attribution.sh").read_text(encoding="utf-8")
        self.assertNotIn("gotsc", launcher.lower())
        self.assertIn("preflight|run|independent|all", launcher)


if __name__ == "__main__":
    unittest.main()
