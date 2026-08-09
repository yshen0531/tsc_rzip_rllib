from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit
    as r51r3,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r51r3_single_transport_return_hold_formal_authority_audit.json"
INDEPENDENT = ROOT / "docs/codex/audit_tools/stage4_2r3c3t13s24d1r14r8r51r3_independent_forensics.py"


def _load_independent():
    spec = importlib.util.spec_from_file_location("r51r3_independent_test", INDEPENDENT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class R51R3FormalAuthorityAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cls.independent = _load_independent()

    @staticmethod
    def _spec(*, weak: bool = False, r_offset: float = 0.0) -> dict:
        return {
            "experiment_id": "unit",
            "slew_scale": 0.9 if weak else 1.0,
            "horizon_steps": 37 if weak else 35,
            "target_R_offset_m": r_offset,
            "target_Z_offset_m": 0.0,
            "target_Ip_offset_A": 0.0,
        }

    @staticmethod
    def _trajectory(horizon: int, *, r: float = 0.75, z: float = 0.0, ip: float = 29779.724):
        return [{"R": r, "Z": z, "Ip": ip} for _ in range(horizon + 1)]

    def test_frozen_config_validates(self) -> None:
        r51r3.validate_config(self.cfg, ROOT)

    def test_deadline_change_is_rejected(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["formal_contract"]["normal_arrival_deadline_step"] = 26
        with self.assertRaisesRegex(ValueError, "frozen design changed"):
            r51r3.validate_config(changed, ROOT)

    def test_exact_target_passes_normal_contract(self) -> None:
        metric = r51r3.formal_metric(
            self._spec(), self._trajectory(35), self.cfg["formal_contract"]
        )
        self.assertTrue(metric["formal_contract_pass"])
        self.assertEqual(metric["formal_best_arrival_ms"], 120)
        self.assertEqual(metric["formal_minimum_signed_margin"], 1.0)

    def test_position_outside_box_fails(self) -> None:
        metric = r51r3.formal_metric(
            self._spec(), self._trajectory(35, r=0.781), self.cfg["formal_contract"]
        )
        self.assertFalse(metric["formal_contract_pass"])
        self.assertLess(metric["formal_minimum_signed_margin"], 0.0)

    def test_weak_contract_uses_370_ms_horizon(self) -> None:
        metric = r51r3.formal_metric(
            self._spec(weak=True), self._trajectory(37), self.cfg["formal_contract"]
        )
        self.assertTrue(metric["formal_contract_pass"])
        with self.assertRaisesRegex(ValueError, "malformed formal trajectory"):
            r51r3.formal_metric(
                self._spec(weak=True), self._trajectory(35), self.cfg["formal_contract"]
            )

    def test_scalar_independent_matches_numpy_path(self) -> None:
        spec = self._spec(weak=True, r_offset=0.01)
        trajectory = self._trajectory(37, r=0.76, z=0.0, ip=29779.724)
        primary = r51r3.formal_metric(spec, trajectory, self.cfg["formal_contract"])
        independent = self.independent.scalar_formal_metric(
            spec, trajectory, self.cfg["formal_contract"]
        )
        self.assertEqual(primary["formal_contract_pass"], independent["formal_contract_pass"])
        self.assertEqual(primary["formal_best_arrival_ms"], independent["formal_best_arrival_ms"])
        for key in ("formal_minimum_signed_margin", "formal_mean_signed_margin"):
            self.assertAlmostEqual(primary[key], independent[key], delta=1e-12)

    def test_authority_detects_repair_and_nonregressing_oracle(self) -> None:
        baseline = {
            "experiment_id": "base",
            "partition": "baseline",
            "pair_id": "p",
            "history_member": "h",
            "candidate_index": -1,
            "candidate_id": "baseline",
            "formal_contract_pass": False,
            "formal_minimum_signed_margin": -0.2,
            "formal_mean_signed_margin": 0.1,
            "formal_best_arrival_ms": 250,
        }
        candidates = []
        for index, candidate_id in enumerate(self.cfg["source_r51r1"]["candidate_ids"], 1):
            candidates.append(
                {
                    **baseline,
                    "experiment_id": f"candidate_{index}",
                    "partition": "candidate",
                    "candidate_index": index,
                    "candidate_id": candidate_id,
                    "formal_contract_pass": index == 1,
                    "formal_minimum_signed_margin": 0.05 if index == 1 else -0.3,
                    "formal_mean_signed_margin": 0.2 if index == 1 else 0.0,
                }
            )
        result = r51r3.authority([baseline, *candidates], 1e-12)
        self.assertEqual(result["failed_baseline_count"], 1)
        self.assertEqual(result["repaired_failed_baseline_count"], 1)
        self.assertEqual(result["measured_oracle_formal_pass_count"], 1)
        self.assertEqual(result["context_rows"][0]["oracle_candidate_index"], 1)

    def test_routes_and_zero_execution_scope_are_frozen(self) -> None:
        self.assertEqual(
            self.cfg["routes"]["authority_insufficient"],
            "REDUCED_Q0_TRANSPORT_BRIDGE_R51R3_SINGLE_TRANSPORT_RETURN_HOLD_AUTHORITY_INSUFFICIENT_SEQUENTIAL_MODEL_REQUIRED",
        )
        self.assertTrue(
            all(
                int(self.cfg["execution_contract"][key]) == 0
                for key in (
                    "new_tsc_count", "new_raw_count", "snapshot_count",
                    "controller_execution_count", "plant_step_count", "model_fit_count",
                    "model_selection_count", "optimization_count",
                )
            )
        )

    def test_design_discloses_pre_freeze_inspection_and_learning_ban(self) -> None:
        design = (ROOT / self.cfg["design_document"]).read_text(encoding="utf-8")
        self.assertIn("before computing or viewing any R51R1 candidate formal metric", design)
        self.assertIn("last R/Z/Ip", design)
        self.assertIn("forbidden from expert data", design)
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])


if __name__ == "__main__":
    unittest.main()
