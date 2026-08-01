from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT
    / "docs/codex/audit_tools/stage4_2r3c3t13s1_transition_forensics.py"
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "t13s1_transition_forensics", TOOL_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trajectory(*, base_shift: float = 0.0) -> list[dict]:
    rows = []
    for step in range(51):
        rows.append(
            {
                "R": 0.72 + base_shift,
                "Z": 0.01 - base_shift,
                "Ip": 30_000.0 + 100.0 * base_shift,
                "currents_a_tsc": [0.0] * 14,
                "wire_currents_a": [base_shift] * 48,
            }
        )
    return rows


def _trace() -> list[dict]:
    return [{"action_norm_tsc": [0.0] * 14} for _ in range(50)]


def _result(
    *,
    pair: str,
    history: str,
    target: str,
    delay: int,
    slew: float,
    sign: int,
    window: str,
    mode: int,
) -> dict:
    first = 3 if window == "transport" else 17
    issue = first - delay - 1
    base_shift = 1e-5 if history == "plus_first" else 0.0
    trajectory = _trajectory(base_shift=base_shift)
    trace = _trace()
    if sign:
        response = np.asarray(
            [2e-4 * (mode + 1), -1e-4, 2.0], dtype=float
        )
        for state in range(first, 51):
            trajectory[state]["R"] += sign * response[0]
            trajectory[state]["Z"] += sign * response[1]
            trajectory[state]["Ip"] += sign * response[2]
            trajectory[state]["currents_a_tsc"][mode] += sign * 0.1
        trace[issue]["action_norm_tsc"][mode] += sign * 0.1 / (3.0 * slew)
    return {
        "spec": {
            "pair_id": pair,
            "history_member": history,
            "target_id": target,
            "action_delay_steps": delay,
            "slew_scale": slew,
            "r3c3_probe_sign": sign,
            "r3c3_probe_window": window,
            "r3c3_probe_mode": mode,
            "r3c3_probe_first_effect_state": first,
            "r3c3_probe_cancel_effect_state": first + 1,
            "formal_horizon_steps": 37 if slew == 0.9 else 35,
            "r3c3_probe_delta_by_task_issue_step": {
                str(issue): [0.0, 0.0, 0.0],
                str(issue + 1): [0.0, 0.0, 0.0],
            },
        },
        "trajectory": trajectory,
        "controller_trace": trace,
    }


def _matrix() -> list[dict]:
    contexts = [
        ("p5", "minus_first", "offset", 2, 0.9),
        ("p5", "plus_first", "offset", 2, 0.9),
        ("p9", "minus_first", "nominal", 0, 1.0),
        ("p9", "plus_first", "nominal", 0, 1.0),
    ]
    rows = []
    for pair, history, target, delay, slew in contexts:
        rows.append(
            _result(
                pair=pair,
                history=history,
                target=target,
                delay=delay,
                slew=slew,
                sign=0,
                window="baseline",
                mode=-1,
            )
        )
        for window in ("transport", "braking"):
            for mode in (0, 1, 2):
                for sign in (-1, 1):
                    rows.append(
                        _result(
                            pair=pair,
                            history=history,
                            target=target,
                            delay=delay,
                            slew=slew,
                            sign=sign,
                            window=window,
                            mode=mode,
                        )
                    )
    assert len(rows) == 52
    return rows


def test_perfect_symmetric_matrix_separates_all_layers():
    tool = _load_tool()
    report = tool.analyze_results(_matrix())
    metrics = report["route_metrics"]
    assert metrics["requested_command_first_issue_symmetry_pass_count"] == 24
    assert metrics["observed_current_first_effect_symmetry_pass_count"] == 24
    assert metrics["plant_first_effect_symmetry_pass_count"] == 24
    assert metrics["plant_full_formal_window_symmetry_pass_count"] == 24
    assert metrics["matched_history_first_effect_pass_count"] == 12
    assert metrics["matched_history_full_formal_window_pass_count"] == 12
    assert metrics["pre_effect_exact_count"] == 24
    assert not metrics["action_resolution_material"]
    assert not metrics["paired_state_or_hidden_history_dependence_material"]


def test_observed_current_asymmetry_is_not_relabelled_as_command_asymmetry():
    tool = _load_tool()
    rows = _matrix()
    changed = copy.deepcopy(rows)
    candidate = next(
        row
        for row in changed
        if row["spec"]["pair_id"] == "p5"
        and row["spec"]["history_member"] == "minus_first"
        and row["spec"]["r3c3_probe_window"] == "transport"
        and row["spec"]["r3c3_probe_mode"] == 0
        and row["spec"]["r3c3_probe_sign"] == 1
    )
    first = candidate["spec"]["r3c3_probe_first_effect_state"]
    candidate["trajectory"][first]["currents_a_tsc"][0] += 0.05
    report = tool.analyze_results(changed)
    metrics = report["route_metrics"]
    assert metrics["requested_command_first_issue_symmetry_pass_count"] == 24
    assert metrics["observed_current_first_effect_symmetry_pass_count"] == 23
    assert metrics["action_resolution_material"]


def test_repository_input_formatter_contract_is_detectable():
    tool = _load_tool()
    text = (ROOT / "tsc_rzip_rllib/core/inputa.py").read_text(encoding="utf-8")
    assert 'f"{float(value):.3E}"' in text
    assert tool.RELATIVE_GATE == 0.10
