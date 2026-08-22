from __future__ import annotations

from decimal import Decimal
import unittest

from scripts import rgeo_zgeo_1ms_1000_hybrid_radial_authority_g1_failure_forensic as forensic


class G1PartialFailureForensicTest(unittest.TestCase):
    def test_observed_slew_excludes_source_effect_and_finds_first_excess(self) -> None:
        currents = (
            (Decimal("0"), Decimal("0")),
            (Decimal("8"), Decimal("8")),
            (Decimal("8.2"), Decimal("8.2")),
            (Decimal("8.50001"), Decimal("8.5")),
        )
        states = [{"current_decimal_a_tsc": row} for row in currents]
        rows = forensic.observed_slew_rows(states)
        self.assertEqual([row["issue_step"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["maximum_observed_delta_a"], "0.2")
        self.assertFalse(rows[0]["exceeds_frozen_cap"])
        self.assertEqual(rows[1]["maximum_observed_delta_a"], "0.30001")
        self.assertTrue(rows[1]["exceeds_frozen_cap"])
        self.assertEqual(rows[1]["maximum_component_indices"], [0])

    def test_routes_preserve_primary_failure(self) -> None:
        self.assertIn("FAIL_STOP", forensic.PRIMARY_FAILURE_ROUTE)
        self.assertIn("FORENSIC_PASS", forensic.PASS_ROUTE)
        self.assertNotEqual(forensic.PRIMARY_FAILURE_ROUTE, forensic.PASS_ROUTE)


if __name__ == "__main__":
    unittest.main()
