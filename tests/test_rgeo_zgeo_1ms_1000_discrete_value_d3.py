from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts import rgeo_zgeo_1ms_1000_discrete_value_d3 as primary

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_1000_discrete_value_d3.json"


def state(index: int, r_mm: float=0, z_mm: float=0, ip_a: float=0) -> dict:
    return {"time_ms":1000+index, "r_geo_m":.7+r_mm/1000, "z_geo_m":z_mm/1000,
            "r_mid_m":.79, "ip_a":30000+ip_a}


class Fixed1000DiscreteValueD3Test(unittest.TestCase):
    def test_identity_budget_roles_and_g3_fail_binding(self) -> None:
        stage, _, _ = primary.load(CONFIG)
        self.assertEqual(primary.b0.sha256(CONFIG), primary.CONFIG_SHA256)
        self.assertEqual((stage["primary_rollouts"], stage["rollouts"]), (14,16))
        self.assertEqual(stage["maximum_advance_attempts"], 768)
        self.assertEqual(stage["data_roles"]["g3_block2"], "retained_negative_development_label_not_rerun")

    def test_matrix_and_cumulative_exact_return_shape(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows = primary.rollout_specs(stage)
        self.assertEqual(sum(r["repeat_index"]==0 for r in rows), 14)
        target_map = {"q0":"q0"}
        for axis in stage["axes"]:
            for sign in ("plus","minus"):
                for level in range(1,5): target_map[f"{axis}_{sign}_level{level}"] = f"{axis}_{sign}_{level}"
        spec = next(r for r in rows if r["conditioner"]=="block4_plus" and r["candidate"]=="odd_minus")
        seq = primary.sequence_for(spec, stage, target_map)
        self.assertEqual(seq[8:20], [f"block4_plus_{x}" if x else "q0" for x in stage["macro_levels"]])
        self.assertEqual(seq[24:36], [f"odd_minus_{x}" if x else "q0" for x in stage["macro_levels"]])
        self.assertTrue(all(x=="q0" for x in seq[36:]))

    def test_metrics_allow_one_weak_axis_but_require_two_and_cone(self) -> None:
        stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        rows=[]
        for spec in primary.rollout_specs(stage):
            if spec["repeat_index"]: continue
            states=[state(i) for i in range(49)]
            if spec["candidate"] != "baseline":
                axis, sign=spec["candidate"].split("_")
                p=1 if sign=="plus" else -1
                for h,m in ((4,.15),(8,.20),(12,.02),(16,.01)):
                    if axis=="even": states[24+h]=state(24+h,r_mm=p*m)
                    elif axis=="odd": states[24+h]=state(24+h,z_mm=p*m)
                    else: states[24+h]=state(24+h,r_mm=p*.005,z_mm=p*.005)
            rows.append({**spec,"states":states})
        metrics=primary.scientific_metrics(rows,stage)
        self.assertTrue(metrics["passed"])
        self.assertEqual([h["supported_axes"] for h in metrics["histories"]],[2,2])

    def test_launcher_modes(self) -> None:
        text=(ROOT/"run_rgeo_zgeo_1ms_1000_discrete_value_d3.sh").read_text(encoding="utf-8")
        for token in ("offline)","run)","audit)","NR1000_D3_SOURCE_REVISION"):
            self.assertIn(token,text)


if __name__ == "__main__": unittest.main()
