from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import types
import unittest
from unittest import mock

import numpy as np

if sys.platform == "win32":
    try:
        import resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification as d1r11,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r11_full_replacement_sequential_transition_identification_370ms.json"


class Stage42R3C3T13S24D1R11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        d1r11._validate_config(copy.deepcopy(self.cfg), CONFIG)
        result = d1r11.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["requested_matrix_rank"], 16)
        self.assertEqual(result["total_real_rollouts"], 1000)
        self.assertEqual(result["feature_dimensions"], {"L": 68, "SA": 133, "Q": 211})

    def test_timing_schedule_and_rl_mutations_fail_closed(self):
        cases = []
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["issue_task_steps"][2] = 16
        cases.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["transition_model"]["tube_multiplier"] = 1.0
        cases.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["normal"]["arrival_deadline_step"] = 26
        cases.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["bc_dagger_or_rl_allowed"] = True
        cases.append(changed)
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    d1r11._validate_config(value, CONFIG)

    def test_matrix_and_prospective_spec_digest_mutations_fail_closed(self):
        changed = copy.deepcopy(self.cfg)
        changed["schedule_contract"]["requested_matrix"][22][0] = -0.24
        with self.assertRaises(ValueError):
            d1r11._validate_config(changed, CONFIG)
        changed = copy.deepcopy(self.cfg)
        changed["source_contract"]["ordered_spec_digest"] = "0" * 64
        with self.assertRaises(ValueError):
            d1r11._validate_config(changed, CONFIG)

    def _table_and_source_specs(self):
        table, specs = [], []
        partitions = ["training"] * 12 + ["calibration"] * 4 + ["holdout"] * 4
        for pair_index, partition in enumerate(partitions):
            for history in ("plus_first", "minus_first"):
                row = {
                    "partition": partition,
                    "pair_id": f"pair_{pair_index:02d}",
                    "history_member": history,
                    "state_generation_experiment_id": f"state_{pair_index:02d}_{history}",
                    "restart_snapshot_manifest_digest": f"digest_{pair_index:02d}_{history}",
                    "restart_snapshot_dir": f"snapshot_{pair_index:02d}_{history}",
                    "target_id": "nominal" if pair_index % 2 else "RZ_p10_m10",
                    "action_delay_steps": 0 if pair_index % 2 else 2,
                    "slew_scale": 1.0 if pair_index % 2 else 0.9,
                    "regime_id": "A",
                }
                table.append(row)
                specs.append(
                    {
                        **copy.deepcopy(row),
                        "r3c3_probe_id": d1r11.s21.BASELINE_PROBE_ID,
                        "horizon_steps": 35 if row["slew_scale"] == 1.0 else 37,
                        "formal_horizon_steps": 35 if row["slew_scale"] == 1.0 else 37,
                        "target_R_offset_m": 0.0,
                        "target_Z_offset_m": 0.0,
                        "target_Ip_offset_A": 0.0,
                    }
                )
        return table, specs

    def test_spec_matrix_is_exactly_1000_and_whole_pair_partitioned(self):
        table, source_specs = self._table_and_source_specs()
        ctx = SimpleNamespace(cfg=self.cfg, base_ctx=object())
        with mock.patch.object(d1r11.s21, "build_specs", return_value=source_specs):
            specs = d1r11.build_specs(ctx, table)
        self.assertEqual(len(specs), 1000)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 1000)
        self.assertEqual(
            {key: sum(row["partition"] == key for row in specs) for key in ("training", "calibration", "holdout")},
            {"training": 600, "calibration": 200, "holdout": 200},
        )
        for pair in {row["pair_id"] for row in specs}:
            self.assertEqual(len({row["partition"] for row in specs if row["pair_id"] == pair}), 1)
        for context in {(row["pair_id"], row["history_member"]) for row in specs}:
            selected = [
                row
                for row in specs
                if (row["pair_id"], row["history_member"]) == context
            ]
            self.assertEqual(len(selected), 25)
            baseline = [row for row in selected if row["s24_role"] == "baseline"]
            self.assertEqual(len(baseline), 1)
            self.assertTrue(
                all(
                    row["baseline_experiment_id"] == baseline[0]["experiment_id"]
                    for row in selected
                    if row["s24_role"] != "baseline"
                )
            )

    def test_transition_item_uses_only_its_own_visible_trajectory(self):
        target = np.asarray([0.7, 0.0, 30000.0])
        trajectory = []
        for step in range(12):
            trajectory.append(
                {
                    "R": 0.7 + 0.001 * step,
                    "Z": -0.0005 * step,
                    "Ip": 30000.0 + 10.0 * step,
                }
            )
        result = {
            "experiment_id": "example",
            "trajectory": trajectory,
            "spec": {
                "horizon_steps": 11,
                "pair_id": "forbidden_pair_label",
                "history_member": "forbidden_history_label",
                "partition": "training",
                "s24_role": "sequential_response",
                "s24_sequence_index": 0,
                "target_R_offset_m": 0.0,
                "target_Z_offset_m": 0.0,
                "target_Ip_offset_A": 0.0,
                "s24_requested_action_by_task_step": {"10": [0.25, 0.25, 0.25, 0.25]},
            },
        }
        item = d1r11._transition_item(
            result, SimpleNamespace(target=target), self.cfg["transition_model"]
        )
        states = item["states"]
        self.assertEqual(states.shape, (12, 5))
        self.assertAlmostEqual(states[10, 0], 1.0 / 3.0)
        self.assertAlmostEqual(states[10, 2], 1.0)
        self.assertEqual(item["forbidden_predictor_input_count"], 0)
        self.assertNotIn("baseline", item)

    def test_issue_and_cancel_use_current_center_and_exact_return(self):
        controller = object.__new__(d1r11.SequentialAmplitudeCodedProbeController)
        controller.schedule_cfg = copy.deepcopy(self.cfg["schedule_contract"])
        controller.issue_steps = (10, 13, 15, 17)
        controller.cancel_steps = (11, 14, 16, 18)
        controller.step = 10
        controller.requested_by_step = {
            10: np.full(4, 0.25),
            11: np.full(4, -0.25),
        }
        basis = np.zeros((4, 14))
        basis[:, :4] = np.eye(4)
        controller._fixed_basis_delta = {
            column: tuple(basis[column].tolist()) for column in range(4)
        }
        controller.turns_tsc = np.ones(14)
        controller.base = SimpleNamespace(
            max_delta_a=1e6,
            min_current=np.full(14, -1e6),
            max_current=np.full(14, 1e6),
        )
        controller.lattice_cfg = {}
        controller._freeze_fixed_basis = mock.Mock()
        center_fields = [d1r11.s21.s16.s9.format_number(0.0) for _ in range(14)]
        target_fields = [
            d1r11.s21.s16.s9.format_number(0.25 if coil < 4 else 0.0)
            for coil in range(14)
        ]
        center = SimpleNamespace(card15_fields=center_fields)
        issued = SimpleNamespace(
            card15_fields=target_fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        cancelled = SimpleNamespace(
            card15_fields=center_fields,
            action_saturated=[False] * 14,
            current_limit_clipped=[False] * 14,
        )
        controller.actuator = SimpleNamespace(
            apply=mock.Mock(side_effect=[center, issued, cancelled])
        )
        actual = tuple(
            d1r11.Decimal("0.25") if coil < 4 else d1r11.Decimal("0")
            for coil in range(14)
        )
        chosen = {
            "action_norm_tsc": [0.0] * 14,
            "incremental_normalized_action_linf": 0.1,
            "total_normalized_action_abs": 0.2,
            "predicted_maximum_current_utilization": 0.3,
            "passed": True,
        }
        with mock.patch.object(
            d1r11.s21,
            "_dynamic_exact_target",
            return_value=(tuple(target_fields), actual, tuple([1] * 14)),
        ), mock.patch.object(
            d1r11.s21.s16.s9,
            "exact_stored_center_action",
            return_value=chosen,
        ):
            _, issue = controller._issue(0, np.zeros(14), np.zeros(14))
            self.assertTrue(issue["passed"])
            self.assertEqual(issue["center_card15_fields"], center_fields)
            controller.step = 11
            _, cancel = controller._cancel(0, np.zeros(14), np.zeros(14))
        self.assertTrue(cancel["passed"])
        self.assertTrue(cancel["criteria"]["exact_zero_target_jump_net"])
        self.assertIsNone(controller._active_issue)

    def test_phase_guard_and_incomplete_resume_fail_closed(self):
        ctx = SimpleNamespace(paths=SimpleNamespace(state=Path("unused")))
        with mock.patch.object(d1r11, "_read_json", return_value={"phase_status": "wrong", "finished": False}):
            with self.assertRaises(ValueError):
                    d1r11._require_phase(ctx, "offline_ready")
        path = mock.Mock()
        path.is_file.return_value = False
        self.assertFalse(d1r11._result_complete(path, {"horizon_steps": 35}))


if __name__ == "__main__":
    unittest.main()
