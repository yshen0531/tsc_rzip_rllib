from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r26_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight
    as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight.json"
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r26_common.sh"


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _source_r22_cfg() -> dict:
    cfg26 = _cfg()
    cfg25 = json.loads((ROOT / cfg26["source_r8r25_config"]).read_text(encoding="utf-8"))
    cfg24 = json.loads((ROOT / cfg25["source_r8r24_config"]).read_text(encoding="utf-8"))
    cfg23 = json.loads((ROOT / cfg24["source_r8r23_config"]).read_text(encoding="utf-8"))
    return json.loads((ROOT / cfg23["source_r8r22_config"]).read_text(encoding="utf-8"))


def _fit_bank() -> list[dict]:
    rng = np.random.default_rng(260809)
    bank = []
    for schedule_index in range(4):
        intervals = []
        previous_q = np.zeros(2)
        for interval, count in enumerate((4, 4, 4, 15)):
            feature = rng.normal(size=42)
            q = np.asarray([schedule_index / 16.0, interval / 16.0])
            row = {
                "interval": interval,
                "feature": feature,
                "q": q,
                "previous_q": previous_q,
            }
            row["expanded"] = primary.r8r23._expanded_row(row)
            row["targets"] = np.asarray(
                [
                    row["expanded"][:5] * 1e-3
                    + offset * np.asarray([1.0, -2.0, 3.0, -4.0, 5.0]) * 1e-5
                    for offset in range(count)
                ]
            )
            intervals.append(row)
            previous_q = q
        bank.append(
            {
                "trajectory_id": f"trajectory_{schedule_index}",
                "schedule_id": f"schedule_{schedule_index}",
                "intervals": intervals,
            }
        )
    return bank


def _transition_bank() -> list[dict]:
    values = (np.asarray([0.0, 0.0]), np.asarray([0.25, 0.0]), np.asarray([0.0, 0.25]))
    bank = []
    for previous_q in values:
        for q in values:
            bank.append(
                {
                    "intervals": [
                        {"previous_q": previous_q.copy(), "q": q.copy()}
                        for _ in range(4)
                    ]
                }
            )
    return bank


class R8R26ContractTests(unittest.TestCase):
    def test_primary_and_independent_validate_frozen_contract(self) -> None:
        cfg = _cfg()
        primary.validate_config(cfg, project_root=ROOT)
        independent._validate_config(cfg)
        self.assertTrue(cfg["schedule_jackknife_contract"]["whole_schedule_exclusion"])
        self.assertFalse(cfg["search_contract"]["global_optimality_claimed"])
        self.assertFalse(cfg["expert_data_allowed"])
        self.assertFalse(cfg["gate_a_qualified"])

    def test_contract_mutations_fail_closed(self) -> None:
        for group, key, value in (
            ("schedule_jackknife_contract", "training_schedule_count", 25),
            ("transition_support_contract", "qhull_joggle_allowed", True),
            ("search_contract", "beam_width", 128),
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("fallback_contract", "pair_or_history_label_allowed", True),
            ("routes", "pass", "changed"),
        ):
            cfg = copy.deepcopy(_cfg())
            cfg[group][key] = value
            with self.assertRaises((KeyError, ValueError)):
                primary.validate_config(cfg, project_root=ROOT)
            with self.assertRaises((KeyError, ValueError)):
                independent._validate_config(cfg)

    def test_schedule_heldout_fit_matches_independent(self) -> None:
        bank = _fit_bank()
        left = primary._fit_selected(
            bank,
            lambda row: row["schedule_id"] != "schedule_0",
            1e-4,
        )
        right = independent._fit_schedule(bank, "schedule_0", 1e-4)
        difference = independent.ind23._maximum_difference(
            primary.r8r23._model_serializable(left),
            independent.ind23._serial(right),
        )
        self.assertLessEqual(difference, 1e-12)

    def test_transition_hulls_and_support_match_independent(self) -> None:
        cfg = _cfg()
        bank = _transition_bank()
        left = primary._transition_hulls(bank, cfg)
        right = independent._transition_hulls(bank, cfg)
        for left_hull, right_hull in zip(left, right):
            self.assertEqual(left_hull["affine_rank"], right_hull["affine_rank"])
            self.assertEqual(left_hull["digest"], right_hull["digest"])
            np.testing.assert_allclose(left_hull["origin"], right_hull["origin"], rtol=0.0, atol=1e-15)
            np.testing.assert_allclose(left_hull["basis"], right_hull["basis"], rtol=0.0, atol=1e-15)
            np.testing.assert_allclose(left_hull["equations"], right_hull["equations"], rtol=0.0, atol=1e-15)
            for previous_q, q, expected in (
                (np.zeros(2), np.asarray([0.125, 0.125]), True),
                (np.zeros(2), np.asarray([0.5, 0.5]), False),
            ):
                self.assertEqual(
                    primary._transition_supported(left_hull, previous_q, q, cfg),
                    expected,
                )
                self.assertEqual(
                    independent._transition_supported(right_hull, previous_q, q, cfg),
                    expected,
                )

    def test_lattice_and_coarse_grid_are_exact(self) -> None:
        cfg = _cfg()
        self.assertEqual(len(primary._all_lattice_units(cfg)), 325)
        r22_cfg = _source_r22_cfg()
        right = independent._coarse_units(r22_cfg, cfg)
        source_r23 = SimpleNamespace(r8r22_ctx=SimpleNamespace(cfg=r22_cfg))
        fake_ctx = SimpleNamespace(
            cfg=cfg,
            source_ctx=SimpleNamespace(
                source_ctx=SimpleNamespace(source_ctx=source_r23)
            ),
        )
        left = primary._coarse_units(fake_ctx)
        self.assertEqual(left, right)
        self.assertEqual(len(left), 33)
        self.assertIn((0, 0), left)

    def test_terminal_rank_prefers_any_robust_pass(self) -> None:
        cfg = _cfg()
        passing = {
            "states": np.zeros((36, 5)),
            "tubes": np.zeros((36, 5)),
            "movement": 10.0,
            "maximum_current": 0.5,
            "tokens": ((0, 0),) * 4,
        }
        failing = copy.deepcopy(passing)
        failing["states"][:, 0] = 2.0
        failing["movement"] = 0.0
        self.assertLess(
            primary._node_rank(passing, terminal=True, deadline=25, endpoint=35, cfg=cfg),
            primary._node_rank(failing, terminal=True, deadline=25, endpoint=35, cfg=cfg),
        )
        self.assertLess(
            independent._rank(passing, True, 25, 35, cfg),
            independent._rank(failing, True, 25, 35, cfg),
        )

    def test_independent_does_not_import_primary_r8r26(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight as",
            source,
        )

    def test_launcher_is_zero_tsc_and_uses_existing_server_venv(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("zero Ray/gotsc/TSC/controller/plant/raw", source)
        self.assertNotIn("ray start", source)
        self.assertNotIn("gotsc", source.replace("zero Ray/gotsc/TSC/controller/plant/raw", ""))


if __name__ == "__main__":
    unittest.main()
