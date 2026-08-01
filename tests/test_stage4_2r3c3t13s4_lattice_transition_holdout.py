from __future__ import annotations

import math
import json

import numpy as np
import pytest

from tsc_rzip_rllib.control.quantized_actuator import QuantizedActuatorModel
from tsc_rzip_rllib.core.inputa import format_number
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s4_lattice_transition_holdout as s4,
)


def _cfg():
    return s4.t11.t1.r3c3.read_json(
        s4._project_root()
        / "configs/stage4_2r3c3t13s4_lattice_transition_holdout_370ms.json"
    )


def _plan(center: float = 0.0):
    cfg = _cfg()["lattice_probe"]
    mode = np.ones(14) / math.sqrt(14)
    current = [center * 1000.0 / 100.0] * 14
    model = QuantizedActuatorModel(
        minimum_current_a_tsc=(-20000.0,) * 14,
        maximum_current_a_tsc=(20000.0,) * 14,
        max_slew_step_a=1000.0,
        turns_tsc=(100.0,) * 14,
    )
    center_result = model.apply(current, [0.0] * 14)
    plan = s4.choose_lattice_displacement(
        center_fields=center_result.card15_fields,
        measured_current_a_tsc=current,
        baseline_action_norm_tsc=[0.0] * 14,
        mode_vector_tsc=mode,
        turns_tsc=[100.0] * 14,
        max_slew_step_a=1000.0,
        minimum_current_a_tsc=[-20000.0] * 14,
        maximum_current_a_tsc=[20000.0] * 14,
        cfg=cfg,
    )
    return cfg, model, current, plan


def test_frozen_config_and_exact_component_count():
    cfg = _cfg()
    s4._validate_config(cfg)
    assert cfg["lattice_probe"]["expected_current_components"] == 26208
    assert 26 * 37 * 14 + 26 * 35 * 14 == 26208


@pytest.mark.parametrize("value", [1.234, -1.234, 1000.0, -1000.0, 0.0])
def test_local_step_is_positive_symmetric_and_round_trips(value):
    field = format_number(value)
    center = s4._decimal_field(field)
    step = s4.local_symmetric_card15_step(field)
    plus = format_number(float(center + step))
    minus = format_number(float(center - step))
    assert step > 0
    assert len(plus) == len(minus) == 10
    assert s4._decimal_field(plus) - center == center - s4._decimal_field(minus)


def test_dynamic_lattice_moves_four_steps_and_reproduces_card_fields():
    _, model, current, plan = _plan()
    assert plan["passed"]
    assert plan["minimum_significant_grid_steps_actual"] >= 4
    assert plan["target_field_central_symmetry_exact"]
    assert plan["coil_space_cosine"] >= 0.98
    assert plan["relative_off_mode_residual"] <= 0.15
    positive = model.apply(current, plan["positive_action_norm_tsc"])
    negative = model.apply(current, plan["negative_action_norm_tsc"])
    assert list(positive.card15_fields) == plan["positive_target_fields"]
    assert list(negative.card15_fields) == plan["negative_target_fields"]


def test_exact_cancellation_uses_negative_issued_field_displacement():
    cfg, model, current, plan = _plan(1.234)
    center = model.apply(current, [0.0] * 14)
    inverse = s4.exact_inverse_lattice_action(
        center_fields=center.card15_fields,
        signed_issue_delta_kAt_tsc=plan["delta_field_kAt_tsc"],
        measured_current_a_tsc=current,
        baseline_action_norm_tsc=[0.0] * 14,
        turns_tsc=[100.0] * 14,
        max_slew_step_a=1000.0,
        minimum_current_a_tsc=[-20000.0] * 14,
        maximum_current_a_tsc=[20000.0] * 14,
        cfg=cfg,
    )
    selected = model.apply(current, inverse["action_norm_tsc"])
    assert inverse["passed"]
    assert inverse["exact_negative_of_issued_displacement"]
    assert list(selected.card15_fields) == inverse["target_fields"]


def test_cancellation_fails_closed_at_current_boundary():
    cfg = _cfg()["lattice_probe"]
    inverse = s4.exact_inverse_lattice_action(
        center_fields=[format_number(1.0)] * 14,
        signed_issue_delta_kAt_tsc=[-10.0] * 14,
        measured_current_a_tsc=[10.0] * 14,
        baseline_action_norm_tsc=[0.0] * 14,
        turns_tsc=[100.0] * 14,
        max_slew_step_a=1.0,
        minimum_current_a_tsc=[-20.0] * 14,
        maximum_current_a_tsc=[20.0] * 14,
        cfg=cfg,
    )
    assert not inverse["passed"]
    assert not inverse["current_bounds_pass"]


def test_blind_guard_requires_complete_development_and_model_hash():
    guard = s4.BlindOpenOrderGuard(expected_development_count=2)
    guard.before_open("development")
    with pytest.raises(ValueError, match="before development model hash"):
        guard.before_open("blind_holdout")
    guard.before_open("development")
    guard.freeze("a" * 64)
    guard.before_open("blind_holdout")
    assert guard.development_open_count == 2
    assert guard.holdout_open_count == 1


def test_blind_guard_rejects_late_development_and_bad_hash():
    guard = s4.BlindOpenOrderGuard(expected_development_count=1)
    guard.before_open("development")
    with pytest.raises(ValueError, match="64 hexadecimal"):
        guard.freeze("bad")
    guard.freeze("b" * 64)
    with pytest.raises(ValueError, match="after T13S4 model freeze"):
        guard.before_open("development")


def test_controller_spec_strips_all_identity_and_history_labels():
    source = {
        "pair_id": "forbidden",
        "history_member": "forbidden",
        "common_prefix_steps": 5,
        "state_generation_experiment_id": "forbidden",
        "baseline_experiment_id": "forbidden",
        "restart_snapshot_dir": "forbidden",
        "restart_snapshot_manifest_digest": "forbidden",
        "experiment_id": "forbidden",
        "environment_variant": "forbidden",
        "kind": "forbidden",
        "phase": "forbidden",
        "category": "forbidden",
        "r3c3t13s4_offline_role": "development",
        "r3c3t13s4_stratum": "hard",
        "r3c3t13s4_source_r3c1_experiment_id": "forbidden",
        "target_id": "nominal",
    }
    output = s4._controller_spec(source)
    assert output == {"target_id": "nominal"}


def test_self_test_is_zero_tsc_and_passes():
    result = s4.self_test()
    json.dumps(result, sort_keys=True, allow_nan=False)
    assert result["passed"]
    assert not result["real_tsc_executed"]
    assert not result["bc_dagger_or_rl_allowed"]
