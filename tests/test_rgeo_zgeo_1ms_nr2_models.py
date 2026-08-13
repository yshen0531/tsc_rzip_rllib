from __future__ import annotations

from decimal import Decimal
import unittest
import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_1ms_nr2_models import Normalizer, fit_arx, q0_readback_bias, recursive_rollout


def trajectory(offset:float)->dict:
    plasma=[]; currents=[]; actions=[]; value=np.asarray([.7+offset,.03,31000.0])
    for step in range(17):
        plasma.append(value.copy());
        if step<16:
            current=np.full(14,offset+step*.01); action=np.full(14,(-1)**step*.1); currents.append(current); actions.append(action); value=value+np.asarray([action.mean()*1e-4,current.mean()*1e-5,-.5])
    frames=[np.concatenate((plasma[s],currents[s],actions[s],[s/16.0,plasma[s][0]-.79])) for s in range(16)]
    return {"plasma":np.asarray(plasma),"currents":np.asarray(currents),"command_deltas":np.asarray(actions),"frames":frames,"r_mid_m":.79}


class OneMsNR2ModelTests(unittest.TestCase):
    def test_q0_readback_bias_uses_q0_coordinate(self)->None:
        readback=tuple(Decimal("1.00001") for _ in range(14))
        q0=tuple(Decimal("1") for _ in range(14))
        self.assertEqual(q0_readback_bias(readback,q0),tuple(Decimal("0.00001") for _ in range(14)))

    def test_structural_arx_shapes_and_recursive_causality(self)->None:
        rows=[trajectory(value) for value in (-.01,0,.01,.02)]; normalizer=Normalizer.fit(rows); model=fit_arx(rows,normalizer,1e-2); prediction=recursive_rollout(model,None,rows[0],normalizer)
        self.assertEqual(prediction.shape,(17,3)); self.assertTrue(np.all(np.isfinite(prediction)))
        modified=trajectory(-.01); modified["plasma"][5:]=999
        self.assertTrue(np.array_equal(prediction,recursive_rollout(model,None,modified,normalizer)))


if __name__=="__main__": unittest.main()
