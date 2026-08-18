import unittest

from scripts import rgeo_zgeo_1ms_id2p1_matched_factorial_development as p1


class ID2P1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage, cls.cfg, cls.targets, cls.source = p1.load()
        cls.streams = p1.campaign_streams(cls.stage, cls.cfg, cls.targets, cls.source)

    def test_cardinality_and_roles(self):
        self.assertEqual(len(self.streams), 42)
        self.assertEqual(len({row["cell_id"] for row in self.streams}), 40)
        self.assertEqual(len({row["group_id"] for row in self.streams}), 8)
        self.assertEqual(sum(row["replay_index"] == 1 for row in self.streams), 2)

    def test_schedule_and_action_bounds(self):
        for row in self.streams:
            self.assertEqual(len(row["targets"]), 34)
            self.assertEqual(len(row["actions"]), 34)
            self.assertTrue(all(float(action["maximum_issued_delta_a"]) <= 0.3 for action in row["actions"]))
            self.assertEqual([action["issue_step"] for action in row["actions"]], list(range(34)))

    def test_factor_coverage(self):
        primary = [row for row in self.streams if row["replay_index"] == 0 and row["cell_kind"] == "probe"]
        self.assertEqual({row["probe_duration_issues"] for row in primary}, {1, 2, 3})
        for group in {row["group_id"] for row in primary}:
            cells = {(row["direction_id"], row["sign"]) for row in primary if row["group_id"] == group}
            self.assertEqual(cells, {("p04","plus"),("p04","minus"),("p07","plus"),("p07","minus")})

    def test_zero_plant_offline(self):
        result = p1.offline(p1.CONFIG, "test")
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual((result["reset_calls"], result["advance_attempts"],
                          result["plant_advance_gotsc_calls"], result["verified_plant_advances"]), (0,0,0,0))


if __name__ == "__main__": unittest.main()
