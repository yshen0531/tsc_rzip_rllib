from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r27_independent_forensics as independent,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator
    as primary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator.json"
LAUNCHER = ROOT / "run_stage4_2r3c3t13s24d1r14r8r27_common.sh"
SOURCE_COMPACT = ROOT / "docs/codex/audits/stage4_2r3c3t13s24d1r14r8r26_result_20260809_a1f4535_v1/compact_audit.json"


def _cfg() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _plan() -> dict:
    return {
        "pair_id": "pair",
        "history_member": "history",
        "coarse_level_count": 33,
        "beam_counts": [26, 90, 256, 32],
        "terminal_seed_count": 32,
        "safe_search_complete": True,
        "selected_plan": {
            "q_units": [[0, 24]] * 4,
            "q_values": [[0.0, 1.5]] * 4,
            "robust_formal_pass": False,
            "worst_formal_margin_violation": 0.5,
            "integrated_normalized_error": 10.0,
            "cumulative_normalized_action_movement": 1.5,
            "maximum_predicted_current_utilization": 0.4,
            "predicted_states": np.zeros((36, 5)).tolist(),
            "reserved_tubes": np.ones((36, 5)).tolist(),
        },
        "robust_formal_plan_found": False,
        "causal_selected_mode": "baseline_fallback",
        "search_counts": {
            "evaluated_sequences": 100,
            "safe_expansions": 50,
            "state_unsupported_nodes": 0,
            "transition_unsupported_expansions": 40,
            "hard_action_rejections": 10,
        },
        "evaluated_sequence_digest": "a" * 64,
        "baseline_formal_pass_for_postselection_scoring": False,
        "hybrid_predicted_formal_pass": False,
    }


class R8R27ContractTests(unittest.TestCase):
    def test_primary_and_independent_validate_frozen_contract(self) -> None:
        cfg = _cfg()
        primary.validate_config(cfg, project_root=ROOT)
        independent._validate_config(cfg)
        self.assertEqual(tuple(cfg["layer_contract"]["ordered_layers"]), primary.LAYERS)
        self.assertFalse(cfg["unchanged_search_contract"]["failed_plan_deployment_allowed"])
        self.assertFalse(cfg["expert_data_allowed"])
        self.assertFalse(cfg["gate_a_qualified"])

    def test_contract_mutations_fail_closed(self) -> None:
        for group, key, value in (
            ("layer_contract", "tube_rescale_allowed", True),
            ("layer_contract", "ordered_layers", ["point_only", "combined_tube"]),
            ("unchanged_search_contract", "beam_width", 128),
            ("formal_contract", "normal_arrival_deadline_step", 26),
            ("classification_gate", "minimum_point_only_oracle_count_for_uncertainty_route", 6),
            ("routes", "uncertainty", "changed"),
        ):
            cfg = copy.deepcopy(_cfg())
            cfg[group][key] = value
            with self.assertRaises(ValueError):
                primary.validate_config(cfg, project_root=ROOT)
            with self.assertRaises(ValueError):
                independent._validate_config(cfg)

    def test_classification_threshold_matches_independent(self) -> None:
        for repairs, oracle, expected in (
            (0, 6, False),
            (1, 6, False),
            (0, 7, False),
            (1, 7, True),
            (3, 9, True),
        ):
            point = {
                "predicted_repaired_failed_baseline_count": repairs,
                "predicted_baseline_fallback_plus_plan_oracle_count": oracle,
            }
            self.assertEqual(primary._point_authority_present(point, _cfg()), expected)
            self.assertEqual(independent._point_authority_present(point, _cfg()), expected)

    def test_plan_summary_digests_match_independent(self) -> None:
        plans = [_plan()]
        left = primary._plan_summaries(plans)
        right = independent._plan_summaries(plans)
        self.assertEqual(left, right)
        self.assertEqual(_digest(left), _digest(right))
        self.assertNotIn("predicted_states", left[0]["selected_plan"])
        self.assertNotIn("reserved_tubes", left[0]["selected_plan"])

    def test_source_compact_fingerprints_match_config(self) -> None:
        cfg = _cfg()
        compact = json.loads(SOURCE_COMPACT.read_text(encoding="utf-8"))
        expected = cfg["source_r8r26"]
        self.assertEqual(_digest(compact["plan_summaries"]), expected["plan_summary_digest"])
        self.assertEqual(
            _digest(compact["transition_hull_evidence"]),
            expected["transition_hull_evidence_digest"],
        )
        self.assertEqual(_digest(compact["coarse_level_units"]), expected["coarse_level_digest"])
        self.assertEqual(compact["pair_tube_digest"], compact["combined_tube_digest"])

    def test_zero_layer_shapes_preserve_source_shapes(self) -> None:
        source = [np.ones((count, 5)) for count in (4, 4, 4, 15)]
        zero = [np.zeros_like(value) for value in source]
        self.assertEqual([value.shape for value in zero], [(4, 5), (4, 5), (4, 5), (15, 5)])
        self.assertTrue(all(np.count_nonzero(value) == 0 for value in zero))

    def test_independent_does_not_import_primary_implementations(self) -> None:
        source = Path(independent.__file__).read_text(encoding="utf-8")
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r27_point_versus_reserve_authority_discriminator as",
            source,
        )
        self.assertNotIn(
            "stage4_2r3c3t13s24d1r14r8r26_action_transition_supported_multiresolution_mpc_preflight as",
            source,
        )

    def test_launcher_is_zero_tsc_and_uses_existing_server_venv(self) -> None:
        source = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn("/home/yangshen0711/tsc_all/tsc_simulation/venv_simu/bin/python", source)
        self.assertIn("zero Ray/gotsc/TSC/controller/plant/raw", source)
        self.assertIn("point-only is optimistic and never deployable", source)
        self.assertNotIn("ray start", source)


if __name__ == "__main__":
    unittest.main()
