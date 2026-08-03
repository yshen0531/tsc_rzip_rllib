from __future__ import annotations

import unittest
import sys
import types

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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r6_physical_state_prefix_reporting_hotfix as audit,
)


class Stage42R3C3T13S24D1R6ReportingHotfixTests(unittest.TestCase):
    def test_state_projection_removes_only_runtime_diagnostics(self):
        row = {
            "R": 0.72,
            "currents_a_tsc": [1.0, 2.0],
            "wire_currents_a": [3.0],
            "gotsc_subprocess_s": 10.0,
            "step_total_s": 11.0,
        }
        self.assertEqual(
            audit._state_projection(row),
            {
                "R": 0.72,
                "currents_a_tsc": [1.0, 2.0],
                "wire_currents_a": [3.0],
            },
        )

    def test_runtime_only_difference_preserves_physical_state_exactness(self):
        source = {
            "R": 0.72,
            "Z": 0.01,
            "Ip": 30_000.0,
            "currents_a_tsc": [1.0],
            "wire_currents_a": [2.0],
            "gotsc_subprocess_s": 10.0,
            "step_total_s": 11.0,
        }
        current = dict(source, gotsc_subprocess_s=12.0, step_total_s=13.0)
        self.assertEqual(
            audit._state_difference_keys(current, source),
            {"gotsc_subprocess_s", "step_total_s"},
        )
        self.assertEqual(
            audit._state_projection(current), audit._state_projection(source)
        )

    def test_physical_difference_is_not_hidden(self):
        source = {"R": 0.72, "gotsc_subprocess_s": 10.0}
        current = {"R": 0.73, "gotsc_subprocess_s": 11.0}
        self.assertEqual(
            audit._state_difference_keys(current, source),
            {"R", "gotsc_subprocess_s"},
        )
        self.assertNotEqual(
            audit._state_projection(current), audit._state_projection(source)
        )

    def test_hotfix_is_bound_to_failed_route_and_old_package(self):
        self.assertEqual(
            audit.EXPECTED_ROUTE,
            "CAUSAL_RECURSIVE_SPLIT_RETURN_SENTINEL_FAIL_REDESIGN_REQUIRED",
        )
        self.assertEqual(audit.EXPECTED_RAW_COUNT, 9)
        self.assertEqual(audit.EXPECTED_RAW_BYTES, 422_133)
        self.assertEqual(len(audit.EXPECTED_RAW_DIGEST), 64)
        self.assertEqual(len(audit.EXPECTED_IMPLEMENTATION_SHA256), 64)


if __name__ == "__main__":
    unittest.main()
