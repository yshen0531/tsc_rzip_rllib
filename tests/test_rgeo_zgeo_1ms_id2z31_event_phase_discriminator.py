import copy
import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_id2z31_event_phase_discriminator as stage
from scripts import rgeo_zgeo_1ms_id2z31_event_phase_discriminator_independent as independent


class ID2Z31Tests(unittest.TestCase):
    def test_config_identity_and_budget(self):
        value = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(stage._sha(stage.CONFIG), stage.CONFIG_SHA256)
        self.assertEqual(value["maximum_rollouts"], 6)
        self.assertEqual(value["maximum_advance_attempts"], 438)
        self.assertEqual(value["event_window_effect_states"], list(range(47, 53)))
        self.assertTrue(all(row.get("data_role", "").startswith("zero_fit")
                            for row in value["rollout_specs"]))

    def test_streams_are_exact_and_close(self):
        cfg, _, runner_cfg, preflight, tracked = stage.load()
        streams = stage.build_streams(cfg, runner_cfg, preflight, tracked)
        self.assertEqual(len(streams), 6)
        self.assertTrue(all(stage.z30.validate_stream(row, runner_cfg)["passed"]
                            for row in streams))
        self.assertEqual(streams[2]["actions"], streams[3]["actions"])
        self.assertEqual([row["phase_issue"] for row in streams],
                         [None, 43, 44, 44, 45, 44])

    @staticmethod
    def _row(family: str, event_state: int):
        states = [{"r_geo_m": -0.001 * i} for i in range(74)]
        states[event_state]["r_geo_m"] = states[event_state - 1]["r_geo_m"] + .0003
        return {"family_id": family, "passed": True, "states": states}

    def test_event_map_records_measured_state(self):
        config = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        rows = [self._row(spec["family_id"], state_index)
                for spec, state_index in zip(config["rollout_specs"], [50, 49, 49, 49, 50, 50])]
        value = stage.event_map(rows, config)
        self.assertTrue(value["passed"])
        self.assertEqual([row["events"][0]["effect_state_index"]
                          for row in value["families"]], [50, 49, 49, 49, 50, 50])
        self.assertEqual(value, independent._event_map(rows, config))

    def test_event_map_fails_missing_or_duplicate(self):
        config = json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        rows = [self._row(spec["family_id"], 50) for spec in config["rollout_specs"]]
        rows[0] = copy.deepcopy(rows[0]); rows[0]["states"][50]["r_geo_m"] = -.050
        self.assertFalse(stage.event_map(rows, config)["passed"])

    def test_alternate_config_and_path_escape_fail(self):
        with self.assertRaises(ValueError):
            stage.load(Path("configs/rgeo_zgeo_1ms_id2z30_fresh_q_model_qualification.json"))
        with self.assertRaises(ValueError):
            stage._inside(stage.ROOT.parent / "outside", "test")


if __name__ == "__main__":
    unittest.main()
