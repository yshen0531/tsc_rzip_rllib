from __future__ import annotations

import argparse
from pathlib import Path
import unittest
from unittest import mock

from docs.codex.audit_tools import (
    stage4_2r3c3t13s7r1_campaign_specific_effect_audit as audit,
)


class Stage42R3C3T13S7R1CampaignSpecificEffectAuditTests(unittest.TestCase):
    @staticmethod
    def _forensic_payload() -> dict:
        return {
            "stage": "Stage4.2R3c3T13S7",
            "conclusion": "S1 is queue-aware; S5 is post-queue immediate",
            "real_tsc_executed": False,
            "summary": {
                "s1_group_count": 24,
                "s1_campaign_contract_match_count": 24,
                "s1_delay2_group_count": 12,
                "s1_delay2_campaign_contract_match_count": 12,
                "s1_delay2_immediate_match_count": 0,
                "s5_group_count": 32,
                "s5_campaign_contract_match_count": 32,
                "s5_immediate_match_count": 32,
                "s5_delay2_group_count": 16,
                "s5_delay2_immediate_match_count": 16,
            },
        }

    def test_effect_forensic_authentication_requires_hash_and_content(self) -> None:
        with mock.patch.object(
            audit.common, "_sha256", return_value=audit.EFFECT_FORENSIC_SHA256
        ), mock.patch.object(
            audit.common, "_strict_json", return_value=self._forensic_payload()
        ):
            payload = audit.authenticate_effect_forensic(Path("forensic.json"))
        self.assertEqual(payload["summary"]["s1_group_count"], 24)

    def test_effect_forensic_rejects_wrong_hash(self) -> None:
        with mock.patch.object(audit.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                audit.authenticate_effect_forensic(Path("forensic.json"))

    def test_r1_enables_campaign_specific_extractor_and_new_route(self) -> None:
        args = argparse.Namespace(source_effect_forensic=Path("forensic.json"))
        base = {
            "stage": "Stage4.2R3c3T13S7",
            "audit_revision": "old",
            "summary": {},
            "passed": False,
            "route": "old",
        }
        with mock.patch.object(
            audit, "authenticate_effect_forensic", return_value=self._forensic_payload()
        ), mock.patch.object(audit.s7, "run_audit", return_value=base) as run:
            output = audit.run_r1_audit(args)
        run.assert_called_once_with(args, campaign_specific_effects=True)
        self.assertEqual(output["stage"], audit.STAGE)
        self.assertEqual(output["route"], audit.FAIL_ROUTE)
        self.assertEqual(output["summary"]["campaign_specific_effect_timing_pass_count"], 56)
        self.assertFalse(output["t13s7_result_rewritten"])

    def test_r1_pass_still_requires_q3_holdout(self) -> None:
        args = argparse.Namespace(source_effect_forensic=Path("forensic.json"))
        base = {"summary": {}, "passed": True, "route": "old"}
        with mock.patch.object(
            audit, "authenticate_effect_forensic", return_value=self._forensic_payload()
        ), mock.patch.object(audit.s7, "run_audit", return_value=base):
            output = audit.run_r1_audit(args)
        self.assertEqual(output["route"], audit.PASS_ROUTE)
        self.assertTrue(output["new_q3_holdout_required_before_controller"])
        self.assertFalse(output["real_mpc_authorized"])
        self.assertFalse(output["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
