import unittest

from scripts import rgeo_zgeo_1ms_1000_restart_semantic_audit_r2 as stage


class Fixed1000SemanticAuditR2Test(unittest.TestCase):
    def test_only_wall_clock_and_cpu_lines_are_normalized(self):
        left = (
            " hello world \n"
            " TSC Version UNX10.8(v152)  : 20 Dec 10       212946.092  20260821  \n"
            "physical payload\n"
            "CPU time (min)  8.8157E-03(segment)  1.8467E-02(cumulative)\n"
        )
        right = left.replace("212946.092", "212948.200").replace(
            "8.8157E-03(segment)  1.8467E-02(cumulative)",
            "8.5513E-03(segment)  1.8365E-02(cumulative)",
        )
        self.assertEqual(stage.normalize_outputa(left)[0], stage.normalize_outputa(right)[0])

    def test_physical_line_difference_is_not_normalized(self):
        left = (
            " TSC Version X  : 20 Dec 10       212946.092  20260821\n"
            "physical A\nCPU time (min)  1(segment)\n"
        )
        right = left.replace("physical A", "physical B")
        self.assertNotEqual(stage.normalize_outputa(left)[0], stage.normalize_outputa(right)[0])


if __name__ == "__main__":
    unittest.main()
