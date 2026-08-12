from __future__ import annotations

import unittest

import numpy as np

from tsc_rzip_rllib.control.rgeo_zgeo_nr2_models import (
    CausalTCNDeltaModel,
    Normalizer,
    build_neural,
    fit_arx,
    parameter_count,
    recursive_rollout,
    teacher_forced_tensors,
)


def synthetic_trajectories(count: int = 6):
    result = []
    for index in range(count):
        state = np.asarray([0.7, 0.03, 31_000.0] + [float(index)] * 14)
        states = [state.copy()]
        actions = []
        for step in range(8):
            action = np.asarray([float((index + step + coil) % 3 - 1) for coil in range(14)])
            state = state + np.concatenate(([1e-4 * action[0], 2e-4 * action[1], action[2]], 0.5 * action))
            actions.append(action)
            states.append(state.copy())
        result.append({"states": states, "actions": actions})
    return result


class NR2ModelTests(unittest.TestCase):
    def test_arx_recursive_shapes_and_finite(self) -> None:
        trajectories = synthetic_trajectories()
        normalizer = Normalizer.fit(np.asarray([row["states"] for row in trajectories]), np.asarray([row["actions"] for row in trajectories]))
        model = fit_arx(trajectories, normalizer, 1e-6)
        prediction = recursive_rollout(model, trajectories[0], normalizer, False)
        self.assertEqual(prediction.shape, (9, 17))
        self.assertTrue(np.all(np.isfinite(prediction)))

    def test_all_neural_candidates_share_shapes_and_budget(self) -> None:
        trajectories = synthetic_trajectories(2)
        normalizer = Normalizer.fit(np.asarray([row["states"] for row in trajectories]), np.asarray([row["actions"] for row in trajectories]))
        inputs, targets = teacher_forced_tensors(trajectories, normalizer)
        self.assertEqual(inputs.shape, (2, 8, 32))
        self.assertEqual(targets.shape, (2, 8, 17))
        for kind in ("gru", "lstm", "tcn"):
            for width in (8, 12):
                model = build_neural(kind, width)
                self.assertEqual(tuple(model(inputs).shape), (2, 8, 17))
                self.assertLessEqual(parameter_count(model), 10_000)
        self.assertIsInstance(build_neural("tcn", 8), CausalTCNDeltaModel)


if __name__ == "__main__":
    unittest.main()
