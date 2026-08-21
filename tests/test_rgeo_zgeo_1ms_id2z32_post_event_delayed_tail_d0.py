import json
from pathlib import Path
import unittest

import numpy as np

from scripts import rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0 as stage
from scripts import rgeo_zgeo_1ms_id2z32_post_event_delayed_tail_d0_independent as independent


class ID2Z32Tests(unittest.TestCase):
    def test_config_identity_budget_and_data_roles(self):
        value=json.loads(stage.CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(stage._sha(stage.CONFIG),stage.CONFIG_SHA256)
        self.assertEqual(value["phase_issue_steps"],[50,56])
        self.assertEqual(value["maximum_rollouts"],10)
        self.assertEqual(value["maximum_advance_attempts"],730)
        self.assertEqual(sum(x["fit_weight"] for x in value["rollout_specs"]),8)
        self.assertTrue(value["delayed_tail_contract"]["all_states_after_issue_are_future_model_targets"])

    def test_streams_exact_complete_and_replay(self):
        config,_,runner_cfg,preflight,tracked=stage.load()
        streams=stage.build_streams(config,runner_cfg,preflight,tracked)
        self.assertEqual(len(streams),10)
        self.assertTrue(all(stage.z31.z30.validate_stream(x,runner_cfg)["passed"] for x in streams))
        self.assertEqual(streams[3]["actions"],streams[9]["actions"])
        self.assertEqual([x["phase_issue"] for x in streams],[None,50,50,50,50,56,56,56,56,50])

    @staticmethod
    def _row(family,phase=None,axis=None,sign=None):
        states=[]
        for k in range(74): states.append({"r_geo_m":-.0003*k,"z_geo_m":.0002*k,"ip_a":31000.0})
        if phase is not None:
            direction={('q_r','plus'):(1,0),('q_r','minus'):(-1,0),('q_z','plus'):(0,1),('q_z','minus'):(0,-1)}[(axis,sign)]
            for k in range(phase+1,74):
                age=min(k-phase,8); states[k]["r_geo_m"]+=direction[0]*.00003*age; states[k]["z_geo_m"]+=direction[1]*.00003*age
        return {"family_id":family,"passed":True,"states":states,"actions":[],"fit_weight":0}

    def test_primary_and_independent_metrics_agree(self):
        config=json.loads(stage.CONFIG.read_text(encoding="utf-8")); rows=[self._row("baseline_transition_center")]
        for phase in (50,56):
            for axis in ("q_r","q_z"):
                for sign in ("plus","minus"): rows.append(self._row(f"issue{phase}__{axis}__{sign}_then_return",phase,axis,sign))
        replay=self._row("replay_issue50__q_z__plus_then_return",50,"q_z","plus")
        replay["actions"]=rows[3]["actions"]
        rows.append(replay)
        left=stage.scientific_metrics(rows,config); right=independent._scientific(rows,config)
        self.assertEqual(left,right); self.assertEqual(len(left["branch_metrics"]),8)

    def test_path_escape_and_alternate_config_fail(self):
        with self.assertRaises(ValueError): stage._inside(stage.ROOT.parent/"outside","test")
        with self.assertRaises(ValueError): stage.load(Path("configs/rgeo_zgeo_1ms_id2z31_event_phase_discriminator.json"))


if __name__=="__main__": unittest.main()
