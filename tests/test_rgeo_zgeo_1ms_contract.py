from __future__ import annotations

import json
import unittest

from tsc_rzip_rllib.control import OneMsControlSpec as PublicOneMsControlSpec
from tsc_rzip_rllib.control.rgeo_zgeo_1ms_contract import (
    CONTROL_PERIOD_MS,
    ONE_MS_CONTRACT_VERSION,
    OneMsCausalHistory,
    OneMsControlSpec,
    OneMsIssuedTargetSlew,
    OneMsRGeoZGeoObservation,
    parse_one_ms_command,
)
from tsc_rzip_rllib.control.rgeo_zgeo_contract import (
    CausalHistory,
    CausalHistoryFrame,
    ContractError,
    DataIdentity,
    IssuedAction,
    QueueEntry,
    RGeoZGeoSignal,
)


def state(time_ms: int, r_shift: float = 0.0) -> dict:
    return {
        "time_ms": time_ms,
        "Ip": -800000.0,
        "abnormal": False,
        "gfile": {
            "boundary_R": [0.55 + r_shift, 0.95 + r_shift, 0.95 + r_shift, 0.55 + r_shift],
            "boundary_Z": [-0.30, -0.30, 0.30, 0.30],
            "limiter_R": [0.45, 1.05, 1.05, 0.45],
            "limiter_Z": [-0.50, -0.50, 0.50, 0.50],
            "ip": -800000.0,
            "xmag": 9.0,
            "zmag": 9.0,
            "rc": 8.0,
            "zc": 8.0,
        },
    }


def action(action_id: str, step: int, target: float) -> IssuedAction:
    return IssuedAction(
        action_id=action_id,
        issue_step=step,
        issue_time_ms=1100 + step,
        issued_action_norm_tsc=(1.0,) * 14,
        serialized_card15_fields=("0.000E+00 ",) * 14,
        quantized_target_current_a_tsc=(target,) * 14,
    )


def frame(
    step: int,
    current: float,
    *,
    r_shift: float = 0.0,
    issued: IssuedAction | None = None,
    queue: tuple[QueueEntry, ...] = (),
    applied_action_id: str | None = None,
    applied_action_age_steps: int | None = None,
    delta: float | None = None,
) -> CausalHistoryFrame:
    return CausalHistoryFrame(
        step_index=step,
        sample_interval_ms=None if step == 0 else CONTROL_PERIOD_MS,
        signal=RGeoZGeoSignal.from_tsc_state(state(1100 + step, r_shift)),
        actual_coil_current_a_tsc=(current,) * 14,
        passive_current_status="unavailable",
        passive_current_a=(),
        missing_observation_fields=("passive_current_a",),
        belief_sequence_id="one-continuous-belief",
        issued_action=issued,
        delay_queue_after_issue=queue,
        applied_action_id=applied_action_id,
        applied_action_age_steps=applied_action_age_steps,
        applied_current_delta_a_tsc=None if delta is None else (delta,) * 14,
    )


def identity() -> DataIdentity:
    return DataIdentity(
        campaign_id="one-ms-nr0-synthetic",
        intended_use="synthetic_fixture",
        declared_before_collection=True,
        source_revision="unit-test",
    )


class OneMsControlSpecTests(unittest.TestCase):
    def test_exact_contract_round_trips(self) -> None:
        payload = OneMsControlSpec().to_dict()
        self.assertEqual(OneMsControlSpec.from_mapping(payload).to_dict(), payload)
        self.assertEqual(PublicOneMsControlSpec().to_dict(), payload)
        self.assertEqual(payload["control_period_ms"], 1)
        self.assertEqual(payload["max_single_turn_coil_delta_a_per_step"], 0.3)
        self.assertTrue(payload["full_limit_allowed"])

    def test_timing_limit_unit_and_unknown_fields_fail_closed(self) -> None:
        payload = OneMsControlSpec().to_dict()
        for mutation in (
            {"control_period_ms": 10},
            {"max_single_turn_coil_delta_a_per_step": 3.0},
            {"full_limit_allowed": False},
            {"single_turn_current_unit": "kA-turn"},
            {"coil_order": "display"},
            {"reserve_headroom": 0.01},
        ):
            with self.assertRaises(ContractError):
                OneMsControlSpec.from_mapping({**payload, **mutation})


class OneMsSignalAndCommandTests(unittest.TestCase):
    def test_same_boundary_center_and_no_fallback(self) -> None:
        observation = OneMsRGeoZGeoObservation.from_tsc_state(state(1100))
        self.assertEqual(observation.signal.boundary.r_geo_m, 0.75)
        self.assertEqual(observation.signal.boundary.z_geo_m, 0.0)
        self.assertEqual(observation.signal.side, "LFS")
        self.assertEqual(observation.to_dict()["contract_version"], ONE_MS_CONTRACT_VERSION)

        invalid = state(1100)
        invalid["gfile"].pop("boundary_R")
        invalid["gfile"].pop("boundary_Z")
        with self.assertRaises(ContractError):
            OneMsRGeoZGeoObservation.from_tsc_state(invalid)

    def test_relative_and_waypoint_commands_are_one_ms_and_ip_free(self) -> None:
        relative = {
            "contract_version": ONE_MS_CONTRACT_VERSION,
            "kind": "relative_endpoint",
            "takeover_time_ms": 1100,
            "duration_ms": 1,
            "delta_r_m": -0.01,
            "delta_z_m": 0.02,
        }
        self.assertEqual(parse_one_ms_command(relative).to_dict(), relative)
        with self.assertRaises(ContractError):
            parse_one_ms_command({**relative, "Ip": -800000.0})

        path = {
            "contract_version": ONE_MS_CONTRACT_VERSION,
            "kind": "waypoint_path",
            "takeover_time_ms": 1100,
            "duration_ms": 3,
            "waypoints": [
                {"elapsed_ms": 0, "r_geo_m": 0.75, "z_geo_m": 0.0},
                {"elapsed_ms": 1, "r_geo_m": 0.74, "z_geo_m": 0.01},
                {"elapsed_ms": 3, "r_geo_m": 0.76, "z_geo_m": -0.01},
            ],
        }
        self.assertEqual(parse_one_ms_command(path).to_dict(), path)


class OneMsSlewAndHistoryTests(unittest.TestCase):
    def test_exact_positive_and_negative_point_three_are_allowed(self) -> None:
        plus = OneMsIssuedTargetSlew(action=action("plus", 0, 0.3), causal_baseline_current_a_tsc=(0.0,) * 14)
        minus = OneMsIssuedTargetSlew(action=action("minus", 0, -0.3), causal_baseline_current_a_tsc=(0.0,) * 14)
        self.assertEqual(plus.maximum_absolute_delta_a, 0.3)
        self.assertEqual(minus.maximum_absolute_delta_a, 0.3)

    def test_any_value_above_point_three_is_rejected_without_tolerance(self) -> None:
        for value in (0.30000000000000004, -0.30000000000000004, 0.300001):
            with self.assertRaisesRegex(ContractError, "exceeds"):
                OneMsIssuedTargetSlew(
                    action=action("over", 0, value),
                    causal_baseline_current_a_tsc=(0.0,) * 14,
                )

    def test_one_ms_history_preserves_crossing_queue_and_belief(self) -> None:
        issued = action("a0", 0, 0.3)
        base = CausalHistory(
            identity=identity(),
            frames=(
                frame(0, 0.0, r_shift=0.01, issued=issued, queue=(QueueEntry("a0", 0),)),
                frame(
                    1,
                    0.3,
                    r_shift=-0.01,
                    applied_action_id="a0",
                    applied_action_age_steps=1,
                    delta=0.3,
                ),
            ),
        )
        qualified = OneMsCausalHistory(
            history=base,
            issued_target_slew=(
                OneMsIssuedTargetSlew(
                    action=issued,
                    causal_baseline_current_a_tsc=(0.0,) * 14,
                ),
            ),
        )
        self.assertEqual([item.signal.side for item in base.frames], ["LFS", "HFS"])
        payload = qualified.to_dict()
        self.assertEqual(payload["contract_version"], ONE_MS_CONTRACT_VERSION)
        self.assertTrue(
            all(
                item["signal"]["contract_version"] == ONE_MS_CONTRACT_VERSION
                for item in payload["frames"]
            )
        )
        json.dumps(payload, allow_nan=False, sort_keys=True)

    def test_ten_ms_history_is_historical_not_convertible(self) -> None:
        old = CausalHistoryFrame(
            **{
                **frame(1, 0.0, delta=0.0).__dict__,
                "sample_interval_ms": 10,
                "signal": RGeoZGeoSignal.from_tsc_state(state(1110)),
            }
        )
        base = CausalHistory(identity=identity(), frames=(frame(0, 0.0), old))
        with self.assertRaisesRegex(ContractError, "1 ms history"):
            OneMsCausalHistory(history=base, issued_target_slew=())

    def test_observed_current_above_point_three_is_rejected(self) -> None:
        base = CausalHistory(
            identity=identity(),
            frames=(frame(0, 0.0), frame(1, 0.30000000000000004, delta=0.30000000000000004)),
        )
        with self.assertRaisesRegex(ContractError, "observed"):
            OneMsCausalHistory(history=base, issued_target_slew=())

    def test_action_slew_record_must_match_causal_frame(self) -> None:
        issued = action("a0", 0, 0.3)
        base = CausalHistory(identity=identity(), frames=(frame(0, 0.0, issued=issued),))
        wrong_baseline = OneMsIssuedTargetSlew(
            action=issued,
            causal_baseline_current_a_tsc=(0.1,) * 14,
        )
        with self.assertRaisesRegex(ContractError, "baseline"):
            OneMsCausalHistory(history=base, issued_target_slew=(wrong_baseline,))

        with self.assertRaisesRegex(ContractError, "all and only"):
            OneMsCausalHistory(history=base, issued_target_slew=())


if __name__ == "__main__":
    unittest.main()
