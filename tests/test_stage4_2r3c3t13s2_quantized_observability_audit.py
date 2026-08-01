from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT
    / "docs/codex/audit_tools/"
    "stage4_2r3c3t13s2_quantized_observability_audit.py"
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "t13s2_quantized_observability", TOOL_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _env(*, minimum: float = -10.0, maximum: float = 10.0) -> dict:
    return {
        "turns_display_order": [100.0] * 14,
        "min_current_a_display_order": [minimum] * 14,
        "max_current_a_display_order": [maximum] * 14,
        "current_slew_a_per_ms": 0.1,
        "dt_ms": 10,
    }


def _result(*, issue_step: int = 0) -> dict:
    trajectory = []
    for step in range(51):
        trajectory.append(
            {
                "R": 0.72 + 1e-5 * step,
                "Z": -0.01 + 2e-5 * step,
                "Ip": 30000.0 + step,
                "currents_a_tsc": [0.0] * 14,
                "wire_currents_a": [float(step)] * 48,
            }
        )
    trace = []
    for step in range(50):
        trace.append(
            {
                "action_norm_tsc": [0.0] * 14,
                "queue_after": [f"causal_{step}"],
                "r3c3_probe_applied_desired_delta": [0.0, 0.0, 0.0],
            }
        )
    return {
        "experiment_id": "synthetic",
        "spec": {
            "pair_id": "forbidden_pair_label",
            "history_member": "plus_first",
            "target_id": "forbidden_target_label",
            "target_R_offset_m": 0.01,
            "target_Z_offset_m": -0.01,
            "target_Ip_offset_A": 0.0,
            "action_delay_steps": 2 if issue_step == 0 else 0,
            "slew_scale": 0.9,
            "r3c3_probe_sign": 1,
            "r3c3_probe_window": "transport",
            "r3c3_probe_mode": 0,
            "r3c3_probe_first_effect_state": 3,
            "r3c3_probe_delta_by_task_issue_step": {
                str(issue_step): [0.0075, 0.0, 0.0],
                str(issue_step + 1): [-0.0075, 0.0, 0.0],
            },
        },
        "trajectory": trajectory,
        "controller_trace": trace,
    }


def test_card15_round_trip_uses_exact_source_formatter_for_both_signs():
    tool = _load_tool()
    current = np.asarray([1.23456, -1.23456] + [0.0] * 12)
    action = np.asarray([0.1, -0.1] + [0.0] * 12)
    row = tool.card15_quantized_next_current(current, action, _env())
    predicted = row["predicted_current_a_tsc"]
    assert predicted[0] == 1.335
    assert predicted[1] == -1.335
    assert all(len(field) == 10 for field in row["card15_fields"])


def test_card15_round_trip_handles_current_clipping_and_zero_action():
    tool = _load_tool()
    current = np.asarray([0.9, -0.9] + [0.0] * 12)
    action = np.asarray([1.0, -1.0] + [0.0] * 12)
    row = tool.card15_quantized_next_current(
        current, action, _env(minimum=-1.0, maximum=1.0)
    )
    assert np.array_equal(row["predicted_current_a_tsc"][:2], [1.0, -1.0])
    assert int(np.sum(row["clipped_components"])) == 2
    zero = tool.card15_quantized_next_current(
        np.zeros(14), np.zeros(14), _env()
    )
    assert np.array_equal(zero["predicted_current_a_tsc"], np.zeros(14))


def test_transition_audit_detects_exact_reconstruction_and_mismatch():
    tool = _load_tool()
    result = _result()
    metrics, _ = tool.audit_actuator_transitions(
        [result], {"synthetic": _env()}
    )
    assert metrics["component_count"] == 700
    assert metrics["exact_component_count"] == 700
    assert metrics["maximum_abs_residual_A"] == 0.0
    changed = copy.deepcopy(result)
    changed["trajectory"][1]["currents_a_tsc"][0] = 0.001
    mismatch, _ = tool.audit_actuator_transitions(
        [changed], {"synthetic": _env()}
    )
    assert mismatch["maximum_abs_residual_A"] >= 0.001
    assert mismatch["within_1e_9_A_component_count"] < 700


def test_exact_collision_with_different_plant_increment_is_alias():
    tool = _load_tool()
    base = {
        "causal_feature_sha256": "same-feature",
        "observed_applied_current_path_sha256": "same-path",
        "development_identity": {"experiment_id": "a"},
        "first_effect_plant_increment_sha256": "plant-a",
    }
    other = copy.deepcopy(base)
    other["development_identity"] = {"experiment_id": "b"}
    other["first_effect_plant_increment_sha256"] = "plant-b"
    result = tool.classify_exact_collisions([base, other])
    assert result["exact_observational_alias_group_count"] == 1
    assert (
        result["route"]
        == "EXACT_OBSERVATIONAL_ALIAS_REQUIRES_SET_VALUED_MODEL"
    )


def test_same_feature_with_different_applied_path_is_not_exact_alias():
    tool = _load_tool()
    rows = [
        {
            "causal_feature_sha256": "same-feature",
            "observed_applied_current_path_sha256": path,
            "development_identity": {"experiment_id": path},
            "first_effect_plant_increment_sha256": plant,
        }
        for path, plant in (("path-a", "plant-a"), ("path-b", "plant-b"))
    ]
    result = tool.classify_exact_collisions(rows)
    assert result["exact_causal_feature_collision_group_count"] == 1
    assert result["exact_observational_alias_group_count"] == 0
    assert result["route"] == "FINITE_CLEAN_SEPARATION_ONLY"


def test_causal_feature_excludes_development_and_hidden_labels():
    tool = _load_tool()
    result = _result(issue_step=0)
    record = tool._issue_record(result)
    encoded = json.dumps(record["causal_feature"], sort_keys=True)
    for forbidden in (
        "pair_id",
        "history_member",
        "target_id",
        "forbidden_pair_label",
        "plus_first",
        "wire_currents",
        "future_probe",
    ):
        assert forbidden not in encoded
    assert record["causal_feature"]["current_measurement"][
        "initial_velocity_unknown"
    ]
