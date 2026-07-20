from __future__ import annotations

import numpy as np

from tsc_rzip_rllib.diagnostics.stage2_trajectory_optimization import (
    _regularize_covariance,
    _sample_gaussian,
    _weighted_elite_statistics,
    build_interpolation_matrix,
    synthetic_stage2_test,
)


def test_interpolation_rows_sum_to_one() -> None:
    matrix = build_interpolation_matrix(10, np.asarray([0, 2, 4, 6, 9], dtype=float))
    assert matrix.shape == (10, 5)
    assert np.allclose(matrix.sum(axis=1), 1.0)
    assert np.all(matrix >= 0.0)


def test_covariance_regularization_is_positive_definite() -> None:
    covariance = np.ones((4, 4))
    repaired = _regularize_covariance(
        covariance,
        eigen_floor=1e-4,
        eigen_ceiling=1.0,
        diagonal_shrinkage=0.1,
    )
    assert np.all(np.linalg.eigvalsh(repaired) >= 1e-4 - 1e-10)


def test_cem_moves_towards_quadratic_target() -> None:
    rng = np.random.default_rng(7)
    target = np.linspace(-0.4, 0.4, 8)
    mean = np.zeros(8)
    covariance = np.eye(8) * 0.25
    before = np.linalg.norm(mean - target)
    for _ in range(6):
        samples = _sample_gaussian(rng, mean, covariance, 128, antithetic=True)
        objective = np.sum((samples - target[None, :]) ** 2, axis=1)
        elite = np.argsort(objective)[:20]
        elite_mean, elite_cov = _weighted_elite_statistics(samples[elite], objective[elite])
        mean = 0.3 * mean + 0.7 * elite_mean
        covariance = _regularize_covariance(
            0.45 * covariance + 0.55 * elite_cov,
            eigen_floor=1e-4,
            eigen_ceiling=1.0,
            diagonal_shrinkage=0.1,
        )
    assert np.linalg.norm(mean - target) < 0.35 * before


def test_synthetic_stage2_test() -> None:
    result = synthetic_stage2_test()
    assert result["interpolation_ok"]
    assert result["gate_ordering_ok"]
