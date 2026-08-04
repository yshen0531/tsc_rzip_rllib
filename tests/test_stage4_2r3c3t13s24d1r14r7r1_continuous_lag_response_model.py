from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import unittest

import numpy as np

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model as primary,
)
from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r7r1_independent_forensics as independent,
)
from tsc_rzip_rllib.control import continuous_lag_response_model as model


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r7r1_continuous_lag_response_model_v1.json"
DESIGN = ROOT / "docs/codex/reports/STAGE4_2R3C3T13S24D1R14R7R1_CONTINUOUS_LAG_RESPONSE_MODEL_DESIGN.md"


class R7R1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    @staticmethod
    def _items() -> list[dict[str, object]]:
        rng = np.random.default_rng(947)
        items: list[dict[str, object]] = []
        for pair in range(4):
            for history in range(2):
                context = 2 * pair + history
                descriptor = rng.normal(size=29)
                for issue in (10, 14, 18, 22):
                    issue_descriptor = descriptor.copy()
                    issue_descriptor[-1] = (issue - 10.0) / 12.0
                    for sign in (-1, 1):
                        for direction in range(4):
                            length = 25 if pair < 2 else 27
                            lag = np.arange(1, length + 1, dtype=float)
                            tau = lag / 27.0
                            response = np.zeros((length, 5))
                            response[:, 2] = sign * (direction + 1) * (
                                0.003 + 0.001 * context
                            ) * (1.0 + 0.2 * tau + 0.1 * tau * tau)
                            response[:, 3] = sign * (0.002 + 0.0002 * issue) * (
                                1.0 - 0.3 * tau
                            )
                            response[:, 4] = (
                                (context - 3.5) * 0.002
                                + sign * direction * 0.0001 * tau
                            )
                            response[:, 0] = np.cumsum(response[:, 2]) / 30.0
                            response[:, 1] = np.cumsum(response[:, 3]) / 30.0
                            items.append(
                                {
                                    "response_id": f"{pair}:{history}:{issue}:{sign}:{direction}",
                                    "context_id": str(context),
                                    "pair_id": f"pair{pair}",
                                    "history_member": str(history),
                                    "issue_task_step": issue,
                                    "sign": sign,
                                    "direction_index": direction,
                                    "descriptor": issue_descriptor.tolist(),
                                    "response": response.tolist(),
                                }
                            )
        return items

    def test_contract(self) -> None:
        primary._validate_config(copy.deepcopy(self.cfg))
        independent._validate(copy.deepcopy(self.cfg))
        self.assertEqual(
            primary.source._sha256(DESIGN), self.cfg["design_document_sha256"]
        )
        self.assertEqual(len(model.candidates(self.cfg)), 27)

    def test_continuous_tail_is_defined_and_independently_reproduced(self) -> None:
        items = self._items()
        train = [item for item in items if item["pair_id"] != "pair3"]
        held = [item for item in items if item["pair_id"] == "pair3"]
        candidate = model.Candidate(4, 3, 0.001)
        fitted = model.fit_model(train, candidate, self.cfg)
        independently_fitted = independent._fit(train, (4, 3, 0.001), self.cfg)
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

    def test_mutations_fail(self) -> None:
        changed = copy.deepcopy(self.cfg)
        changed["model_contract"]["temporal_legendre_degrees"] = [2, 3, 4]
        with self.assertRaises(ValueError):
            primary._validate_config(changed)
        with self.assertRaises(ValueError):
            independent._validate(changed)

    def test_independent_separate(self) -> None:
        text = inspect.getsource(independent)
        self.assertNotIn("continuous_lag_response_model as model", text)
        self.assertNotIn("r7r1_continuous_lag_response_model as", text)

    def test_zero_tsc(self) -> None:
        self.assertFalse(self.cfg["execution_contract"]["tsc_executed"])
        self.assertFalse(self.cfg["scientific_scope"]["bc_dagger_or_rl_allowed"])


if __name__ == "__main__":
    unittest.main()
