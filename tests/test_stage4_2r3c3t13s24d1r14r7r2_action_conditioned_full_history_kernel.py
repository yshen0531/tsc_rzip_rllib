from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel as primary,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r2_independent_forensics as independent,
)
from tsc_rzip_rllib.control import action_conditioned_history_response_model as model


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r7r2_action_conditioned_full_history_kernel_v1.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R7R2_ACTION_CONDITIONED_FULL_HISTORY_KERNEL_DESIGN.md"


class R7R2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    @staticmethod
    def _items() -> list[dict[str, object]]:
        rng = np.random.default_rng(71472)
        items: list[dict[str, object]] = []
        for pair in range(4):
            for history in range(2):
                context = 2 * pair + history
                base_descriptor = rng.normal(size=142)
                for issue in (10, 14, 18, 22):
                    descriptor = base_descriptor.copy()
                    descriptor[-1] = (issue - 10.0) / 12.0
                    for sign in (-1, 1):
                        for direction in range(4):
                            scales = [1.0]
                            if issue > 10 and direction == 0:
                                scales.append(1.5)
                            for action_scale in scales:
                                length = 25 if pair < 2 else 27
                                lag = np.arange(1, length + 1, dtype=float)
                                tau = lag / 27.0
                                response = np.zeros((length, 5))
                                nonlinear = 1.0 + 0.15 * (action_scale - 1.0) * context
                                response[:, 2] = (
                                    sign
                                    * action_scale
                                    * nonlinear
                                    * (direction + 1)
                                    * (0.002 + 0.0002 * context)
                                    * (1.0 + 0.2 * tau)
                                )
                                response[:, 3] = sign * action_scale * 0.003 * (1.0 - 0.1 * tau)
                                response[:, 4] = (context - 3.5) * 0.001 + sign * 0.0001 * tau
                                response[:, 0] = np.cumsum(response[:, 2]) / 30.0
                                response[:, 1] = np.cumsum(response[:, 3]) / 30.0
                                canonical = action_scale == 1.0
                                operational = direction != 0 or issue == 10 or action_scale == 1.5
                                roles = (["canonical"] if canonical else []) + (
                                    ["operational"] if operational else []
                                )
                                items.append(
                                    {
                                        "response_id": f"{pair}:{history}:{issue}:{sign}:{direction}:{action_scale}",
                                        "source_stage": "R6" if action_scale == 1.5 else ("R2" if issue == 10 else "R4"),
                                        "context_id": str(context),
                                        "pair_id": f"pair{pair}",
                                        "history_member": str(history),
                                        "issue_task_step": issue,
                                        "sign": sign,
                                        "direction_index": direction,
                                        "action_scale": action_scale,
                                        "geometry_roles": roles,
                                        "descriptor": descriptor.tolist(),
                                        "response": response.tolist(),
                                    }
                                )
        return items

    def test_contract(self) -> None:
        primary._validate_config(copy.deepcopy(self.cfg))
        independent._validate(copy.deepcopy(self.cfg))
        self.assertEqual(primary.source._sha256(DESIGN), self.cfg["design_document_sha256"])
        self.assertEqual(len(model.candidates(self.cfg)), 27)

    def test_synthetic_bank_and_independent_tail(self) -> None:
        items = self._items()
        self.assertEqual(len(items), 304)
        self.assertEqual(sum("canonical" in item["geometry_roles"] for item in items), 256)
        self.assertEqual(sum("operational" in item["geometry_roles"] for item in items), 256)
        train = [item for item in items if item["pair_id"] != "pair3"]
        held = [item for item in items if item["pair_id"] == "pair3"]
        candidate = model.Candidate(4, 0.5, 0.1)
        fitted = model.fit_model(train, candidate, self.cfg)
        independently_fitted = independent._fit(train, (4, 0.5, 0.1), self.cfg)
        for item in held:
            predicted = model.predict_item(fitted, item, self.cfg)
            independently_predicted = independent._predict(
                independently_fitted, item, self.cfg
            )
            self.assertEqual(predicted.shape, (27, 5))
            self.assertTrue(np.all(np.isfinite(predicted)))
            np.testing.assert_allclose(
                predicted, independently_predicted, rtol=1e-10, atol=1e-12
            )

    def test_mutations_fail_closed(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["bank_contract"]["history_offsets"] = list(range(22))
        with self.assertRaises(ValueError):
            primary._validate_config(changed)
        with self.assertRaises(ValueError):
            independent._validate(changed)

    def test_independent_implementation_is_separate(self) -> None:
        text = inspect.getsource(independent)
        self.assertNotIn("action_conditioned_history_response_model", text)
        self.assertNotIn("r7r2_action_conditioned_full_history_kernel as", text)

    def test_zero_tsc_and_expert_block(self) -> None:
        self.assertFalse(self.cfg["execution_contract"]["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["expert_data_allowed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
