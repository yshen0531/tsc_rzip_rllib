import copy
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r3_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r3_sign_split_response_feasibility_v1.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R3_SIGN_SPLIT_RESPONSE_FEASIBILITY_DESIGN.md"


def _trajectory(direction=None, sign=0):
    rows = []
    for index in range(15):
        r = 1.5
        z = 0.0
        ip = 1_000_000.0
        if direction is not None and index >= 11:
            if direction == 0:
                r += sign * 0.0003
            elif direction == 1:
                z += sign * 0.0003
            elif direction == 2:
                ip += sign * 100.0
            elif direction == 3:
                r += sign * 0.00001 * (index - 10)
        rows.append({"R": r, "Z": z, "Ip": ip})
    return rows


def _fixture():
    specs = []
    results = {}
    for context_index in range(8):
        context = f"context_{context_index}"
        base_id = f"{context}_baseline"
        base_spec = {
            "experiment_id": base_id,
            "source_d1r13_experiment_id": context,
            "d1r14r2_role": "baseline",
            "d1r14r2_direction_index": -1,
            "d1r14r2_sign": 0,
            "pair_id": f"pair_{context_index // 2}",
            "history_member": "plus_first" if context_index % 2 == 0 else "minus_first",
        }
        specs.append(base_spec)
        results[base_id] = {"trajectory": _trajectory(), "controller_trace": [{}] * 14}
        for direction in range(4):
            for sign in (1, -1):
                experiment_id = f"{context}_{direction}_{sign}"
                spec = {
                    "experiment_id": experiment_id,
                    "source_d1r13_experiment_id": context,
                    "d1r14r2_role": "signed_probe",
                    "d1r14r2_direction_index": direction,
                    "d1r14r2_sign": sign,
                    "pair_id": base_spec["pair_id"],
                    "history_member": base_spec["history_member"],
                }
                coordinate = np.asarray([1.0, 2.0, 3.0, 4.0]) * sign
                field = np.asarray([5.0, 6.0, 7.0, 8.0]) * sign
                trace = [{} for _ in range(14)]
                trace[10] = {
                    "r3c3t13s24d1r14r2_event_detail": {
                        "requested_coordinate": coordinate.tolist(),
                        "actual_signed_delta_field_kAt_tsc": field.tolist(),
                    }
                }
                specs.append(spec)
                results[experiment_id] = {
                    "trajectory": _trajectory(direction, sign),
                    "controller_trace": trace,
                }
    return specs, results


class Stage42R3C3T13S24D1R14R3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_design_and_zero_tsc_contract(self):
        primary._validate_config(self.cfg, ROOT, DESIGN)
        self.assertEqual(primary._sha256(DESIGN), self.cfg["design_document_sha256"])
        execution = self.cfg["execution_contract"]
        self.assertEqual(execution["new_raw_count"], 0)
        self.assertFalse(execution["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])

    def test_gate_or_architecture_mutation_fails_closed(self):
        changed = copy.deepcopy(self.cfg)
        changed["sign_split_contract"]["maximum_condition_number"] = 21.0
        with self.assertRaisesRegex(ValueError, "frozen sign-split contract changed"):
            primary._validate_config(changed, ROOT, DESIGN)
        changed = copy.deepcopy(self.cfg)
        changed["sign_split_contract"]["cross_sign_response_symmetry_is_acceptance_gate"] = True
        with self.assertRaisesRegex(ValueError, "frozen sign-split contract changed"):
            primary._validate_config(changed, ROOT, DESIGN)

    def test_r2_failed_geometry_is_reproduced_not_relabelled(self):
        geometry = {
            "passed": False,
            "signal_pass_count": 32,
            "symmetry_pass_count": 28,
            "rank_pass_count": 8,
            "condition_pass_count": 8,
            "minimum_odd_peak_normalized_outputs5": 0.005466000000009519,
            "maximum_even_to_odd_peak_ratio": 0.8528017842241936,
            "maximum_condition_number": 8.802962394477525,
            "pair_rows": [
                {"direction_index": index, "symmetry_pass": False}
                for index in range(4)
            ],
        }
        result = primary._r2_reproduced(self.cfg, geometry)
        self.assertTrue(result["passed"])
        self.assertFalse(result["original_geometry_passed"])
        self.assertEqual(result["failed_pair_count"], 4)

    def test_primary_and_independent_synthetic_branches_agree(self):
        specs, results = _fixture()
        first = primary._sign_split_geometry(self.cfg, specs, results)
        grouped = {
            (
                str(spec["source_d1r13_experiment_id"]),
                str(spec["d1r14r2_role"]),
                int(spec["d1r14r2_direction_index"]),
                int(spec["d1r14r2_sign"]),
            ): results[str(spec["experiment_id"])]
            for spec in specs
        }
        second = independent._recompute_branches(self.cfg, specs, grouped)
        self.assertTrue(first["passed"])
        self.assertTrue(second["passed"])
        self.assertTrue(independent._close(first, second))
        self.assertEqual(first["branch_count"], 16)
        self.assertEqual(first["signal_pass_count"], 64)
        self.assertEqual(first["rank_pass_count"], 16)

    def test_issue_symmetry_is_raw_event_exact(self):
        specs, results = _fixture()
        result = primary._issue_symmetry(specs, results)
        self.assertTrue(result["passed"])
        self.assertEqual(result["coordinate_exact_count"], 32)
        self.assertEqual(result["physical_field_exact_count"], 32)
        broken = copy.deepcopy(results)
        experiment_id = next(
            spec["experiment_id"]
            for spec in specs
            if spec["d1r14r2_role"] == "signed_probe"
            and spec["d1r14r2_direction_index"] == 0
            and spec["d1r14r2_sign"] == -1
            and spec["source_d1r13_experiment_id"] == "context_0"
        )
        broken[experiment_id]["controller_trace"][10][
            "r3c3t13s24d1r14r2_event_detail"
        ]["actual_signed_delta_field_kAt_tsc"][0] += 1.0
        self.assertFalse(primary._issue_symmetry(specs, broken)["passed"])

    def test_strict_json_rejects_duplicates_and_nonstandard_numbers(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            primary._strict_loads('{"x": 1, "x": 2}')
        with self.assertRaisesRegex(ValueError, "nonstandard JSON constant"):
            primary._strict_loads('{"x": NaN}')

    def test_launchers_use_server_venv_and_forbid_tsc(self):
        shell = (ROOT / "scripts/stage4_2r3c3t13s24d1r14r3_shell_common.sh").read_text(encoding="utf-8")
        common = (ROOT / "run_stage4_2r3c3t13s24d1r14r3_common.sh").read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", shell)
        self.assertIn("zero controller/plant/Ray/gotsc/TSC", common)
        self.assertNotIn("ray start", common.lower())
        self.assertNotIn(" gotsc ", common.lower())


if __name__ == "__main__":
    unittest.main()
