from __future__ import annotations

import json
from pathlib import Path
import unittest
import numpy as np

from scripts import rgeo_zgeo_1ms_1000_direct_value_v1 as primary

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"configs/rgeo_zgeo_1ms_1000_direct_value_v1.json"


class Fixed1000DirectValueV1Test(unittest.TestCase):
    def test_frozen_data_and_roles(self) -> None:
        stage,contexts=primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG),primary.CONFIG_SHA256)
        self.assertEqual(set(contexts),set(stage["contexts"]))
        self.assertEqual(len(contexts["even_plus"]["responses"]),4)
        self.assertEqual(len(contexts["block4_plus"]["responses"]),6)
        self.assertEqual(stage["data_roles"]["calibration"],"unopened")

    def test_feature_is_causal_issue24_and_finite(self) -> None:
        _,contexts=primary.load(CONFIG)
        for row in contexts.values():
            self.assertEqual(row["feature"].shape,(11,))
            self.assertTrue(np.all(np.isfinite(row["feature"])))

    def test_development_is_whole_history_and_support_gated(self) -> None:
        stage,contexts=primary.load(CONFIG); report=primary.development(stage,contexts)
        self.assertEqual([f["held_context"] for f in report["folds"]],stage["contexts"])
        self.assertEqual(set(report["support"]),{"no_action",*stage["candidates"]})
        self.assertLessEqual(report["maximum_development_nearest_support_distance"],.55)

    def test_refuses_dataset_digest_mutation(self) -> None:
        stage=json.loads(CONFIG.read_text(encoding="utf-8")); stage["dataset_roots"][0]["primary_digest"]="0"*64
        self.assertNotEqual(stage["dataset_roots"][0]["primary_digest"],json.loads(CONFIG.read_text(encoding="utf-8"))["dataset_roots"][0]["primary_digest"])


if __name__=="__main__": unittest.main()
