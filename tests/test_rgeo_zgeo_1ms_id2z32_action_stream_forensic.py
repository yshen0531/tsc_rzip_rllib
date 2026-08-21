import unittest

from scripts import rgeo_zgeo_1ms_id2z32_action_stream_forensic as forensic


class ID2Z32ActionStreamForensicTest(unittest.TestCase):
    def test_frozen_action_stream_defect(self):
        value = forensic.execute()
        self.assertTrue(value["passed"], value["failures"])
        self.assertTrue(value["issue56_all_four_streams_identical_to_baseline"])
        self.assertTrue(value["issue50_action_separation_reproduced"])
        self.assertEqual(value["plant_advances"], 0)
        self.assertEqual(value["models_fit_or_updated"], 0)


if __name__ == "__main__":
    unittest.main()
