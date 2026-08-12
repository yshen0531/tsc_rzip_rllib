from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
import json

import numpy as np

from scripts.rgeo_zgeo_nr2_collect import _sha256, _targets
from tsc_rzip_rllib.control.rgeo_zgeo_nr2_spec import NR2_CAMPAIGN_ID, build_nr2_specs


class FakeConfig:
    turns_tsc = np.asarray([480.0] * 8 + [200.0] * 2 + [100.0] * 4)
    max_delta_current_a_per_step = 3.0


class NR2CollectorTests(unittest.TestCase):
    def test_targets_are_card15_quantized_around_one_center(self) -> None:
        source = np.linspace(-100.0, 100.0, 14)
        spec = build_nr2_specs()[0]
        targets = _targets(FakeConfig(), source, spec.normalized_actions_tsc)
        self.assertEqual(len(targets), 8)
        self.assertTrue(all(len(target.serialized_card15_fields) == 14 for target in targets))
        active = [np.asarray(target.quantized_current_a_tsc) for action, target in zip(spec.normalized_actions_tsc, targets) if any(action)]
        holds = [np.asarray(target.quantized_current_a_tsc) for action, target in zip(spec.normalized_actions_tsc, targets) if not any(action)]
        self.assertTrue(active and holds)
        for hold in holds[1:]:
            np.testing.assert_array_equal(hold, holds[0])

    def test_authorization_hash_primitives_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(dir=".") as name:
            root = Path(name)
            bundle = root / "frozen_models.pt"
            bundle.write_bytes(b"frozen")
            payload = {
                "campaign_id": NR2_CAMPAIGN_ID,
                "source_revision": "abc",
                "holdout_authorized": True,
                "frozen_model_sha256": [_sha256(bundle)],
            }
            encoded = json.loads(json.dumps(payload))
            self.assertEqual(encoded["frozen_model_sha256"], [_sha256(bundle)])
            bundle.write_bytes(b"changed")
            self.assertNotEqual(encoded["frozen_model_sha256"], [_sha256(bundle)])


if __name__ == "__main__":
    unittest.main()
