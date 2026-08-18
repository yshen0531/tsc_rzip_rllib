import copy
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/rgeo_zgeo_1ms_id2o0_causal_support_readiness_audit.py"
SPEC = importlib.util.spec_from_file_location("id2o0", SCRIPT)
id2o0 = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(id2o0)


class ID2O0Tests(unittest.TestCase):
    def setUp(self):
        self.stage = json.loads(id2o0.CONFIG.read_text(encoding="utf-8"))

    def test_frozen_identity_and_zero_plant_contract(self):
        self.assertEqual(self.stage["stage"], "ID-2O0")
        self.assertEqual(self.stage["execution_contract"], "server_read_only_zero_tsc_zero_model_fit")
        self.assertEqual(self.stage["prediction_horizons_ms"], list(range(1, 9)))
        self.assertEqual(self.stage["data_roles"]["n1_holdout"], "unopened_forbidden")

    def test_prefix_vector_has_only_frozen_causal_inputs(self):
        row = json.loads((ROOT / self.stage["inputs"]["k1_directory"] /
                          "h00__p04_plus_i25_d3__r0.json").read_text(encoding="utf-8"))
        vector = id2o0.prefix_vector(row, 25, self.stage)
        self.assertEqual(vector.shape, (96,))

    def test_signature_keeps_duration_and_relative_timing(self):
        krow = json.loads((ROOT / self.stage["inputs"]["k1_directory"] /
                           "h00__p04_plus_i25_d3__r0.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(krow)
        changed["probe_duration_issues"] = 2
        self.assertNotEqual(id2o0.schedule_signature(krow), id2o0.schedule_signature(changed))

    def test_gate_is_conjunction(self):
        structure = {"fit_eligible_independent_families": 16,
                     "fit_eligible_families_by_probe_duration": {"1": 2, "2": 2, "3": 2}}
        support = {"exact_schedule_support_fraction": 0.75, "probe_count": 8,
                   "positive_nearest_response_directions": 7, "nearest_response_nrmse": 0.75}
        ranking = {"maximum_regret_fraction": 0.25}
        self.assertTrue(all(id2o0.gate_results(structure, support, ranking, self.stage).values()))
        support["nearest_response_nrmse"] = 0.750001
        self.assertFalse(all(id2o0.gate_results(structure, support, ranking, self.stage).values()))

    def test_config_mutation_fails_closed(self):
        changed = copy.deepcopy(self.stage)
        changed["causal_prefix"]["future_actual_current"] = "allowed"
        path = ROOT / ".codex_tmp" / "id2o0_mutated_config.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(changed), encoding="utf-8")
        try:
            with self.assertRaises(id2o0.IntegrityError):
                id2o0.load_stage(path)
        finally:
            path.unlink(missing_ok=True)

    def test_independent_script_imports_from_script_path(self):
        script = ROOT / "scripts/rgeo_zgeo_1ms_id2o0_causal_support_readiness_independent.py"
        completed = subprocess.run([sys.executable, str(script), "--help"], cwd=ROOT,
                                   check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
