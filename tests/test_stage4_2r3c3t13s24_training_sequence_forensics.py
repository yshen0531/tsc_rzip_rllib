import json
import unittest

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24_training_sequence_forensics as forensic,
)


class Stage42R3C3T13S24TrainingSequenceForensicsTests(unittest.TestCase):
    def test_structured_cancel_failure_is_recovered(self):
        event = {
            "event": "sequential_cancel",
            "slot": 2,
            "task_step": 16,
            "criteria": {"actuator_gate": False, "incremental_action": False},
        }
        reason = "ValueError('S24 sequential cancel action failed: " + json.dumps(event) + "')"
        self.assertEqual(forensic._failure_event(reason), event)

    def test_forbidden_trace_flags_only_actual_access(self):
        clean = {
            "task_step": 10,
            "measurement_max_state_index_used": 10,
            "future_measurement_used": False,
            "r3c3t13s24_pair_history_partition_label_used": False,
        }
        forbidden = dict(clean, future_measurement_used=True)
        self.assertEqual(forensic._forbidden_trace_count([clean]), 0)
        self.assertEqual(forensic._forbidden_trace_count([clean, forbidden]), 1)

    def test_s23r1_event_index_rejects_incomplete_evidence(self):
        with self.assertRaisesRegex(ValueError, "coverage changed"):
            forensic._static_event_index({"event_rows": []})


if __name__ == "__main__":
    unittest.main()
