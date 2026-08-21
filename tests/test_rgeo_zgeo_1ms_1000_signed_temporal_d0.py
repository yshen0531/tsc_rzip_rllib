from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0 as primary
from scripts import rgeo_zgeo_1ms_1000_signed_temporal_d0_independent as independent


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_signed_temporal_d0.json"


def state(index: int, r_mm: float = 0.0, z_mm: float = 0.0, ip_a: float = 0.0) -> dict:
    return {
        "time_ms": 1000 + index,
        "r_geo_m": 0.7 + r_mm / 1000.0,
        "z_geo_m": z_mm / 1000.0,
        "r_mid_m": 0.79,
        "ip_a": 30000.0 + ip_a,
    }


def source_record() -> dict:
    return {
        **state(0),
        "actual_current_a_tsc": [0.0] * 14,
        "wire_current_a": [0.0] * 48,
        "artifact_sha256": {name: name for name in primary.SEMANTIC_ARTIFACTS},
    }


class Fixed1000SignedTemporalD0Test(unittest.TestCase):
    def test_frozen_identity_budget_and_roles(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual(payload["issue_phases"], [8, 10, 24])
        self.assertEqual(payload["rollouts"], 14)
        self.assertEqual(payload["maximum_advance_attempts"], 560)
        self.assertEqual(payload["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(payload["data_roles"]["critical_replays"], "integrity_only_zero_fit_weight")
        self.assertEqual(payload["data_roles"]["calibration"], "unopened")
        self.assertEqual(payload["data_roles"]["holdout"], "unopened")

    def test_rollout_matrix_and_replay_weights(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(payload)
        self.assertEqual(len(rows), 14)
        self.assertEqual(sum(row["repeat_index"] == 0 for row in rows), 12)
        self.assertEqual(sum(row["repeat_index"] == 1 for row in rows), 2)
        self.assertTrue(all(
            row["data_role"] == "integrity_only_zero_fit_weight"
            for row in rows if row["repeat_index"] == 1
        ))

    def test_sequence_has_exact_four_issue_pulse(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        spec = primary.rollout_specs(payload)[0]
        targets = {"q0": "q0", "even_plus": "pulse"}
        sequence = primary.sequence_for(spec, payload, targets)
        self.assertEqual(len(sequence), 40)
        self.assertEqual([index for index, value in enumerate(sequence) if value == "pulse"], [8, 9, 10, 11])
        self.assertEqual(sequence[12], "q0")

    def test_scientific_metrics_pass_clean_two_axis_signed_geometry(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(index) for index in range(41)]
        rows = []
        for spec in primary.rollout_specs(payload):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(41)]
            sign = 1.0 if spec["sign"] == "plus" else -1.0
            for horizon in (4, 8):
                index = spec["issue_phase"] + horizon
                if spec["axis"] == "even":
                    states[index] = state(index, r_mm=0.10 * sign)
                else:
                    states[index] = state(index, z_mm=0.10 * sign)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, baseline, payload)
        self.assertTrue(metrics["passed"])
        self.assertTrue(all(
            abs(row["condition"] - 1.0) < 1e-12
            for phase in metrics["phases"] for row in phase["horizons"]
        ))

    def test_scientific_metrics_reject_collinear_outputs(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        baseline = [state(index) for index in range(41)]
        rows = []
        for spec in primary.rollout_specs(payload):
            if spec["repeat_index"]:
                continue
            states = [state(index) for index in range(41)]
            sign = 1.0 if spec["sign"] == "plus" else -1.0
            for horizon in (4, 8):
                index = spec["issue_phase"] + horizon
                states[index] = state(index, r_mm=0.10 * sign)
            rows.append({**spec, "states": states})
        metrics = primary.scientific_metrics(rows, baseline, payload)
        self.assertFalse(metrics["phase_geometry_pass"])
        self.assertFalse(metrics["passed"])

    def test_source_gate_is_exact_and_checks_complete_currents(self) -> None:
        expected = source_record()
        self.assertEqual(primary.source_mismatch_reasons(source_record(), expected), [])
        changed = source_record()
        changed["wire_current_a"] = changed["wire_current_a"][:-1]
        self.assertIn(
            "SOURCE_WIRE_CURRENT_A_LENGTH",
            primary.source_mismatch_reasons(changed, expected),
        )
        changed = source_record()
        changed["r_geo_m"] += 2e-12
        self.assertIn("SOURCE_R_GEO_M", primary.source_mismatch_reasons(changed, expected))

    def test_raw_source_audit_uses_card15_not_rewritten_inputa_hash(self) -> None:
        expected = source_record()
        raw = {
            **state(0),
            "current_a_tsc": tuple([0.0] * 14),
            "wire_a": tuple([0.0] * 48),
        }

        def artifact_hash(path: Path) -> str:
            return path.name

        with mock.patch.object(primary.b0, "sha256", side_effect=artifact_hash) as sha:
            self.assertEqual(independent._source_reasons(ROOT, "rollout", raw, expected), [])
        checked_names = {Path(call.args[0]).name for call in sha.call_args_list}
        self.assertNotIn("inputa", checked_names)
        self.assertEqual(checked_names, {"geqdsk", "coil_currents.csv", "wire_currents.csv"})

    def test_launcher_exposes_only_offline_run_and_audit(self) -> None:
        text = (ROOT / "run_rgeo_zgeo_1ms_1000_signed_temporal_d0.sh").read_text(encoding="utf-8")
        self.assertIn("NR1000_D0_SOURCE_REVISION", text)
        self.assertIn("offline)", text)
        self.assertIn("run)", text)
        self.assertIn("audit)", text)


if __name__ == "__main__":
    unittest.main()
