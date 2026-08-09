import copy
import inspect
import json
import unittest
from pathlib import Path

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8r48_independent_forensics as independent48,
)
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8r48_q0_to_transport_causal_bridge_support_audit
    as r8r48,
)


class R8R48CausalBridgeSupportAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.config_path = cls.root / "configs" / (
            "stage4_2r3c3t13s24d1r14r8r48_"
            "q0_to_transport_causal_bridge_support_audit.json"
        )
        cls.cfg = json.loads(cls.config_path.read_text(encoding="utf-8"))

    @staticmethod
    def _candidates():
        return [
            {"index": 0, "id": "q0", "q": np.zeros(4)},
            {"index": 1, "id": "d0p", "q": np.asarray([1.0, 0.0, 0.0, 0.0])},
        ]

    @staticmethod
    def _trajectory(name, schedule, q1=None, q2=None, state12=0.0):
        q1 = np.zeros(4) if q1 is None else np.asarray(q1, dtype=float)
        q2 = np.zeros(4) if q2 is None else np.asarray(q2, dtype=float)
        states = np.zeros((20, 5), dtype=float)
        states[12, 0] = state12
        raw = [
            {
                "currents_a_tsc": [float(index)] * 14,
                "visible": [0.0, 0.0, 0.0],
            }
            for index in range(20)
        ]
        decisions = [10, 12, 14, 16, 18, 22]
        qs = [np.zeros(4), q1, q2, np.zeros(4), np.zeros(4), np.zeros(4)]
        previous = np.zeros(4)
        intervals = []
        for index, (decision, q) in enumerate(zip(decisions, qs)):
            intervals.append(
                {
                    "interval": index,
                    "decision": decision,
                    "feature": np.zeros(44),
                    "q": q,
                    "previous_q": previous.copy(),
                    "targets": np.zeros((1, 5)),
                }
            )
            previous = q
        return {
            "trajectory_id": name,
            "pair_id": "pair0",
            "history_member": "q1",
            "schedule_id": schedule,
            "source": "synthetic",
            "states": states,
            "trajectory": raw,
            "intervals": intervals,
        }

    def test_frozen_config(self):
        r8r48.validate_config(self.cfg, project_root=self.root)
        self.assertEqual(self.cfg["bridge_contract"]["required_bridge_cell_count"], 256)
        self.assertFalse(
            self.cfg["geometric_diagnostic_contract"][
                "geometric_support_substitutes_for_physical_bridge"
            ]
        )
        self.assertFalse(self.cfg["scientific_scope"]["gate_a_qualified"])

    def test_frozen_config_mutations_fail_closed(self):
        for section, key, value in (
            ("bridge_contract", "primary_transport_task_step", 14),
            ("bridge_contract", "later_interval_substitution_allowed", True),
            (
                "geometric_diagnostic_contract",
                "geometric_support_substitutes_for_physical_bridge",
                True,
            ),
            ("scientific_scope", "model_fit_allowed", True),
        ):
            changed = copy.deepcopy(self.cfg)
            changed[section][key] = value
            with self.assertRaisesRegex(ValueError, "frozen config changed"):
                r8r48.validate_config(changed, project_root=self.root)

    def test_exact_q0_prefix_then_interval_one_candidate_is_authentic(self):
        q = np.asarray([1.0, 0.0, 0.0, 0.0])
        q0 = self._trajectory("q0", "q0")
        bridge = self._trajectory("bridge", "bridge", q1=q)
        result = r8r48.enumerate_bridges([q0, bridge], self._candidates())
        self.assertEqual(result["required_bridge_cell_count"], 1)
        self.assertEqual(result["authentic_bridge_cell_count"], 1)
        self.assertTrue(result["complete_physical_bridge_support"])
        self.assertEqual(result["cells"][0]["authentic_bridge_trajectory_ids"], ["bridge"])

    def test_metadata_match_without_exact_physical_prefix_is_not_bridge(self):
        q = np.asarray([1.0, 0.0, 0.0, 0.0])
        q0 = self._trajectory("q0", "q0")
        changed = self._trajectory("changed", "bridge", q1=q, state12=1e-12)
        result = r8r48.enumerate_bridges([q0, changed], self._candidates())
        self.assertEqual(result["authentic_bridge_cell_count"], 0)
        self.assertEqual(result["metadata_only_bridge_cell_count"], 1)
        self.assertFalse(result["complete_physical_bridge_support"])

    def test_later_candidate_does_not_substitute_for_interval_one(self):
        q = np.asarray([1.0, 0.0, 0.0, 0.0])
        q0 = self._trajectory("q0", "q0")
        later = self._trajectory("later", "later", q2=q)
        result = r8r48.enumerate_bridges([q0, later], self._candidates())
        self.assertEqual(result["authentic_bridge_cell_count"], 0)
        self.assertEqual(result["later_interval_candidate_cell_count"], 1)

    def test_prefix_digest_includes_raw_current_and_visible_state(self):
        left = self._trajectory("left", "q0")
        right = copy.deepcopy(left)
        self.assertEqual(r8r48._prefix_payload(left), r8r48._prefix_payload(right))
        right["trajectory"][12]["currents_a_tsc"][3] += 1e-9
        self.assertNotEqual(r8r48._prefix_payload(left), r8r48._prefix_payload(right))

    def test_route_distinguishes_absent_and_present_without_claiming_execution(self):
        common = {
            "q0_reference_context_count": 16,
            "nonzero_candidate_count": 16,
            "required_bridge_cell_count": 256,
        }
        absent = r8r48.assemble_result(
            self.cfg,
            {"passed": True},
            {"trajectory_count": 560},
            {**common, "complete_physical_bridge_support": False},
            {},
        )
        present = r8r48.assemble_result(
            self.cfg,
            {"passed": True},
            {"trajectory_count": 560},
            {**common, "complete_physical_bridge_support": True},
            {},
        )
        self.assertEqual(absent["route"], self.cfg["routes"]["support_absent"])
        self.assertEqual(present["route"], self.cfg["routes"]["support_present"])
        self.assertFalse(absent["real_tsc_executed"])
        self.assertFalse(present["gate_a_qualified"])

    def test_independent_enumerator_is_not_primary_enumerator(self):
        self.assertIsNot(independent48._enumerate, r8r48.enumerate_bridges)
        source = inspect.getsource(independent48._enumerate)
        self.assertNotIn("enumerate_bridges", source)
        self.assertNotIn("r8r48.enumerate", source)

    def test_argument_closure_preserves_all_source_paths(self):
        self.assertEqual(len(r8r48.ARGUMENT_NAMES), len(set(r8r48.ARGUMENT_NAMES)))
        self.assertIn("r8r46-run", r8r48.ARGUMENT_NAMES)
        self.assertIn("r8r44-run", r8r48.ARGUMENT_NAMES)
        self.assertIn("source-stage42r3c3-bank-dir", r8r48.ARGUMENT_NAMES)


if __name__ == "__main__":
    unittest.main()
