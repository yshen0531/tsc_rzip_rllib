from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from docs.codex.audit_tools import stage4_2r3c3t13s7r1_support_forensic as forensic


class Stage42R3C3T13S7R1SupportForensicTests(unittest.TestCase):
    def test_distribution_preserves_frozen_support_threshold(self) -> None:
        result = forensic._distribution([0.10, 0.15, 0.16, 0.80])
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["frozen_support_pass_count"], 2)
        self.assertEqual(result["minimum"], 0.10)
        self.assertEqual(result["maximum"], 0.80)

    def test_empty_distribution_is_strict_json_safe(self) -> None:
        self.assertEqual(
            forensic._distribution([]),
            {
                "count": 0,
                "minimum": None,
                "median": None,
                "maximum": None,
                "frozen_support_pass_count": 0,
            },
        )

    def test_source_authentication_rejects_wrong_hash(self) -> None:
        with mock.patch.object(forensic.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                forensic.authenticate_r1(Path("r1.json"))


if __name__ == "__main__":
    unittest.main()
