from __future__ import annotations

import argparse
from pathlib import Path
import unittest
from unittest import mock

from docs.codex.audit_tools import (
    stage4_2r3c3t13s8_first_effect_transition_audit as audit,
)


class Stage42R3C3T13S8FirstEffectTransitionAuditTests(unittest.TestCase):
    def test_design_authentication_rejects_wrong_hash(self) -> None:
        with mock.patch.object(audit.common, "_sha256", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                audit.authenticate_design(Path("design.md"))

    def test_wrapper_enables_only_frozen_t13s8_changes(self) -> None:
        args = argparse.Namespace(
            design=Path("design.md"),
            source_effect_forensic=Path("effect.json"),
            source_r1_audit=Path("r1.json"),
        )
        base = {"summary": {}, "passed": False, "route": "old"}
        with mock.patch.object(audit, "authenticate_design"), mock.patch.object(
            audit.r1, "authenticate_effect_forensic"
        ), mock.patch.object(
            audit.support_forensic, "authenticate_r1"
        ), mock.patch.object(audit.s7, "run_audit", return_value=base) as run:
            output = audit.run_t13s8_audit(args)
        run.assert_called_once_with(
            args,
            campaign_specific_effects=True,
            single_transition=True,
            all_training_hypotheses=True,
        )
        self.assertEqual(output["route"], audit.FAIL_ROUTE)
        self.assertTrue(output["first_effect_transition_only"])
        self.assertFalse(output["adjacent_cancellation_transition_used"])
        self.assertFalse(output["real_mpc_authorized"])

    def test_pass_still_requires_q3_holdout(self) -> None:
        args = argparse.Namespace(
            design=Path("design.md"),
            source_effect_forensic=Path("effect.json"),
            source_r1_audit=Path("r1.json"),
        )
        with mock.patch.object(audit, "authenticate_design"), mock.patch.object(
            audit.r1, "authenticate_effect_forensic"
        ), mock.patch.object(
            audit.support_forensic, "authenticate_r1"
        ), mock.patch.object(
            audit.s7, "run_audit", return_value={"summary": {}, "passed": True}
        ):
            output = audit.run_t13s8_audit(args)
        self.assertEqual(output["route"], audit.PASS_ROUTE)
        self.assertTrue(output["new_q3_holdout_required_before_controller"])
        self.assertFalse(output["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
