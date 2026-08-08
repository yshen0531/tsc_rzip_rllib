from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r18_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r18_second_order_boolean_ridge_loco_preflight as preflight,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r18_second_order_boolean_ridge_loco_preflight.json"


class SecondOrderBooleanRidgeLocoPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_source_hashes(self) -> None:
        preflight.validate_config(self.cfg, project_root=ROOT)
        design = ROOT / self.cfg["design_document"]
        source = ROOT / self.cfg["source_r8r15_config"]
        self.assertEqual(hashlib.sha256(design.read_bytes()).hexdigest(), self.cfg["design_document_sha256"])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), self.cfg["source_r8r15_config_sha256"])

    def test_exact_development_calibration_and_missing_partition(self) -> None:
        contract = self.cfg["code_contract"]
        development = tuple(contract["development_codes"])
        calibration = tuple(contract["calibration_codes"])
        missing = tuple(contract["missing_codes"])
        cube = {"".join(symbols) for symbols in __import__("itertools").product("UV", repeat=4)}
        self.assertEqual(set(development) | set(calibration) | set(missing), cube)
        self.assertFalse((set(development) | set(calibration)) & set(missing))
        self.assertEqual(missing, ("UVUU", "UUVU", "UVVU", "VUUV", "VVUV", "VUVV"))

    def test_matrix_geometry_and_frozen_feature_order(self) -> None:
        development = self.cfg["code_contract"]["development_codes"]
        measured = [*development, *self.cfg["code_contract"]["calibration_codes"]]
        x_dev = preflight.design_matrix(development)
        x_full = preflight.design_matrix(measured)
        cube = sorted({"".join(symbols) for symbols in __import__("itertools").product("UV", repeat=4)})
        x_cube = preflight.design_matrix(cube)
        self.assertEqual(np.linalg.matrix_rank(x_dev), 6)
        self.assertEqual(np.linalg.matrix_rank(x_full), 9)
        self.assertEqual(np.linalg.matrix_rank(x_cube), 11)
        self.assertLessEqual(np.linalg.cond(x_cube), 1.01)
        self.assertTrue(np.array_equal(preflight.code_row("UVVU"), [1, 1, -1, -1, 1, -1, -1, 1, 1, -1, -1]))
        self.assertTrue(np.array_equal(preflight.code_row("UVUV"), [1, 1, -1, 1, -1, -1, 1, -1, -1, 1, -1]))
        stability = preflight._stability(self.cfg, measured, self.cfg["code_contract"]["missing_codes"])
        self.assertEqual(stability["measured_rank"], 9)
        self.assertEqual(stability["cube_rank"], 11)
        self.assertLessEqual(stability["maximum_loco_normal_condition"], 32.0)
        self.assertLessEqual(stability["maximum_loco_weight_l2"], 1.30)
        self.assertLessEqual(stability["maximum_missing_weight_absolute"], 0.67)

    def test_augmented_svd_matches_frozen_ridge_normal_equation(self) -> None:
        measured = self.cfg["code_contract"]["measured_codes"][:-1]
        rng = np.random.default_rng(1608)
        responses = [rng.normal(size=(7, 3)) for _ in measured]
        penalty = preflight.penalty_matrix(self.cfg)
        fitted = preflight.fit_svd(measured, responses, penalty=penalty, rcond=1e-12)
        x = preflight.design_matrix(measured)
        y = np.asarray(responses)
        expected = np.linalg.solve(x.T @ x + penalty, x.T @ y.reshape(len(measured), -1)).reshape(11, 7, 3)
        self.assertTrue(np.allclose(fitted, expected, rtol=1e-12, atol=1e-12))

    def test_response_and_prediction_preserve_prefix_and_apply_only_rzi(self) -> None:
        baseline = {"trajectory": [{"R": float(i), "Z": -float(i), "Ip": 1000.0 + i, "keep": i} for i in range(13)]}
        candidate = copy.deepcopy(baseline)
        for row in candidate["trajectory"][10:]:
            row["R"] += 0.001
            row["Z"] -= 0.002
            row["Ip"] += 5.0
        delta = preflight._response(candidate, baseline, 10)
        rebuilt = preflight._predicted_result(baseline, delta, 10)
        self.assertEqual(rebuilt["trajectory"][:10], baseline["trajectory"][:10])
        self.assertEqual(rebuilt["trajectory"], candidate["trajectory"])

    def test_contract_rejects_gate_code_and_learning_mutation(self) -> None:
        mutations = (
            ("calibration_gates", "maximum_scaled_point_error", 0.11),
            ("model_contract", "pair_ridge_lambda", 9),
            ("scientific_scope", "expert_data_allowed", True),
        )
        for section, key, value in mutations:
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen design"):
                preflight.validate_config(changed, project_root=ROOT)
        changed = copy.deepcopy(self.cfg)
        changed["code_contract"]["missing_codes"][0] = "UUUU"
        with self.assertRaisesRegex(ValueError, "frozen design"):
            preflight.validate_config(changed, project_root=ROOT)

    def test_routes_separate_source_model_authority_and_physical_sentinel(self) -> None:
        routes = self.cfg["routes"]
        self.assertEqual(len(set(routes.values())), 4)
        self.assertIn("SOURCE_OR_INTEGRITY_FAIL_NO_TSC", routes["source_fail"])
        self.assertIn("MODEL_INADEQUATE", routes["model_fail"])
        self.assertIn("CONTINUOUS_MULTIDIRECTION", routes["authority_fail"])
        self.assertIn("FRESH_MISSING_SEQUENCE_SENTINEL_REQUIRED", routes["pass"])
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_primary_and_independent_model_implementations_are_separate(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r18_second_order_boolean_ridge_loco_preflight as",
            source,
        )
        self.assertIn("np.linalg.solve", source)
        self.assertIn("np.linalg.svd", inspect.getsource(preflight.fit_svd))
        self.assertNotIn("fit_svd", source)
        self.assertIn("for right in range(left + 1, 4)", source)
        self.assertIn("formal_margin_buffer", inspect.getsource(preflight.compute))

    def test_launcher_uses_existing_server_venv_and_zero_tsc_commands(self) -> None:
        launcher = (ROOT / "run_stage4_2r3c3t13s24d1r14r8r18_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", launcher)
        self.assertIn("primary|independent|postprocess", launcher)
        self.assertIn("R8R16_RUN", launcher)
        self.assertIn("R8R17_RUN", launcher)
        self.assertIn("zero new TSC", launcher)
        self.assertNotIn("python3", launcher)
        self.assertNotIn("tar ", launcher)
        self.assertNotIn("unzip", launcher)
        self.assertNotIn("zip ", launcher)


if __name__ == "__main__":
    unittest.main()
