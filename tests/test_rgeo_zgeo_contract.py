from __future__ import annotations

import copy
import json
import unittest

from tsc_rzip_rllib.control import (
    CONTRACT_VERSION,
    CausalHistory,
    CausalHistoryFrame,
    ContractError,
    DataIdentity,
    IssuedAction,
    IpConstraintContract,
    QueueEntry,
    RGeoZGeoSignal,
    parse_rgeo_zgeo_command,
)


def synthetic_state(time_ms: int = 1100, r_shift: float = 0.0):
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
            # Explicitly conflicting legacy alternatives must not be used.
            "xmag": 9.0,
            "zmag": 9.0,
            "rc": 8.0,
            "zc": 8.0,
        },
    }


def action(action_id: str, step: int, time_ms: int) -> IssuedAction:
    return IssuedAction(
        action_id=action_id,
        issue_step=step,
        issue_time_ms=time_ms,
        issued_action_norm_tsc=(0.1,) * 14,
        serialized_card15_fields=("0.000E+00 ",) * 14,
        quantized_target_current_a_tsc=(0.0,) * 14,
    )


class SignalContractTests(unittest.TestCase):
    def test_exact_bounding_box_center_and_side(self):
        signal = RGeoZGeoSignal.from_tsc_state(synthetic_state())
        self.assertEqual(signal.boundary.r_geo_m, 0.75)
        self.assertEqual(signal.boundary.z_geo_m, 0.0)
        self.assertEqual(signal.limiter.r_inner_m, 0.45)
        self.assertEqual(signal.limiter.r_outer_m, 1.05)
        self.assertEqual(signal.limiter.r_mid_m, 0.75)
        self.assertEqual(signal.side, "LFS")

        hfs = RGeoZGeoSignal.from_tsc_state(synthetic_state(r_shift=-0.01))
        self.assertEqual(hfs.side, "HFS")

    def test_boundary_must_be_explicit_paired_same_state_data(self):
        for mutation in (
            lambda g: g.pop("boundary_R"),
            lambda g: g.pop("boundary_Z"),
            lambda g: g.update(boundary_Z=[-0.1, 0.1]),
            lambda g: g.update(boundary_R=[0.5, float("nan"), 0.8, 0.9]),
            lambda g: g.update(boundary_R=[0.5] * 4),
        ):
            state = synthetic_state()
            mutation(state["gfile"])
            with self.assertRaises(ContractError):
                RGeoZGeoSignal.from_tsc_state(state)

    def test_no_magnetic_axis_centroid_or_alias_fallback(self):
        state = synthetic_state()
        state["gfile"].pop("boundary_R")
        state["gfile"].pop("boundary_Z")
        state["gfile"]["xplot"] = [0.5, 0.9, 0.9, 0.5]
        state["gfile"]["zplot"] = [-0.2, -0.2, 0.2, 0.2]
        with self.assertRaises(ContractError):
            RGeoZGeoSignal.from_tsc_state(state)

    def test_invalid_limiter_or_ip_fails_closed(self):
        state = synthetic_state()
        state["gfile"]["limiter_Z"] = [0.1, 0.2, 0.3, 0.4]
        with self.assertRaises(ContractError):
            RGeoZGeoSignal.from_tsc_state(state)

        state = synthetic_state()
        state["Ip"] += 1.0
        with self.assertRaisesRegex(ContractError, "same step"):
            RGeoZGeoSignal.from_tsc_state(state)

        state = synthetic_state()
        state["abnormal"] = True
        with self.assertRaises(ContractError):
            RGeoZGeoSignal.from_tsc_state(state)


class CommandContractTests(unittest.TestCase):
    def test_relative_endpoint_has_no_ip_and_fixed_takeover(self):
        payload = {
            "contract_version": CONTRACT_VERSION,
            "kind": "relative_endpoint",
            "takeover_time_ms": 1100,
            "duration_ms": 600,
            "delta_r_m": -0.08,
            "delta_z_m": 0.03,
        }
        command = parse_rgeo_zgeo_command(payload)
        self.assertEqual(command.to_dict(), payload)
        self.assertNotIn("Ip", command.to_dict())
        with self.assertRaises(ContractError):
            parse_rgeo_zgeo_command({**payload, "Ip": -800000.0})
        with self.assertRaises(ContractError):
            parse_rgeo_zgeo_command({**payload, "takeover_time_ms": 1110})

    def test_waypoint_geometry_and_order_are_explicit(self):
        payload = {
            "contract_version": CONTRACT_VERSION,
            "kind": "waypoint_path",
            "takeover_time_ms": 1100,
            "duration_ms": 800,
            "waypoints": [
                {"elapsed_ms": 0, "r_geo_m": 0.80, "z_geo_m": 0.00},
                {"elapsed_ms": 300, "r_geo_m": 0.70, "z_geo_m": 0.05},
                {"elapsed_ms": 800, "r_geo_m": 0.82, "z_geo_m": -0.02},
            ],
        }
        command = parse_rgeo_zgeo_command(payload)
        self.assertEqual(command.to_dict(), payload)
        bad = copy.deepcopy(payload)
        bad["waypoints"][1]["elapsed_ms"] = 800
        with self.assertRaises(ContractError):
            parse_rgeo_zgeo_command(bad)

    def test_ip_is_separate_soft_and_hard_contract(self):
        contract = IpConstraintContract(
            soft_reference_a=-800000.0,
            soft_tolerance_a=10000.0,
            hard_min_a=-900000.0,
            hard_max_a=-700000.0,
        )
        self.assertTrue(contract.validate_observation(-800000.0))
        self.assertFalse(contract.validate_observation(-650000.0))
        with self.assertRaises(ContractError):
            contract.validate_observation(float("nan"))


class CausalHistoryContractTests(unittest.TestCase):
    def frame(
        self,
        step: int,
        r_shift: float,
        current: float,
        *,
        issued: IssuedAction | None,
        queue=(),
        applied_id=None,
        applied_age=None,
        delta=None,
        belief="shared-belief",
    ) -> CausalHistoryFrame:
        return CausalHistoryFrame(
            step_index=step,
            sample_interval_ms=None if step == 0 else 10,
            signal=RGeoZGeoSignal.from_tsc_state(
                synthetic_state(time_ms=1100 + 10 * step, r_shift=r_shift)
            ),
            actual_coil_current_a_tsc=(current,) * 14,
            passive_current_status="unavailable",
            passive_current_a=(),
            missing_observation_fields=("passive_current_a",),
            belief_sequence_id=belief,
            issued_action=issued,
            delay_queue_after_issue=tuple(queue),
            applied_action_id=applied_id,
            applied_action_age_steps=applied_age,
            applied_current_delta_a_tsc=None if delta is None else (delta,) * 14,
        )

    def identity(self):
        return DataIdentity(
            campaign_id="nr0-synthetic",
            intended_use="synthetic_fixture",
            declared_before_collection=True,
            source_revision="unit-test",
        )

    def test_crossing_keeps_one_history_and_explicit_action_stages(self):
        issued = action("a0", 0, 1100)
        frames = (
            self.frame(0, 0.02, 0.0, issued=issued, queue=(QueueEntry("a0", 0),)),
            self.frame(
                1,
                -0.02,
                1.0,
                issued=None,
                queue=(),
                applied_id="a0",
                applied_age=1,
                delta=1.0,
            ),
        )
        history = CausalHistory(identity=self.identity(), frames=frames)
        self.assertEqual([frame.signal.side for frame in history.frames], ["LFS", "HFS"])
        self.assertEqual({frame.belief_sequence_id for frame in history.frames}, {"shared-belief"})
        json.dumps(history.to_dict(), sort_keys=True, allow_nan=False)

    def test_future_queue_reference_and_belief_reset_are_rejected(self):
        with self.assertRaisesRegex(ContractError, "future action"):
            CausalHistory(
                identity=self.identity(),
                frames=(self.frame(0, 0.0, 0.0, issued=None, queue=(QueueEntry("future", 0),)),),
            )

        issued = action("a0", 0, 1100)
        with self.assertRaisesRegex(ContractError, "must not reset"):
            CausalHistory(
                identity=self.identity(),
                frames=(
                    self.frame(0, 0.01, 0.0, issued=issued),
                    self.frame(1, -0.01, 0.0, issued=None, delta=0.0, belief="reset"),
                ),
            )

    def test_readback_delta_and_data_identity_fail_closed(self):
        with self.assertRaisesRegex(ContractError, "readback"):
            CausalHistory(
                identity=self.identity(),
                frames=(
                    self.frame(0, 0.0, 0.0, issued=None),
                    self.frame(1, 0.0, 1.0, issued=None, delta=0.5),
                ),
            )
        with self.assertRaisesRegex(ContractError, "before collection"):
            DataIdentity(
                campaign_id="retroactive",
                intended_use="expert",
                declared_before_collection=False,
                source_revision="x",
            )


if __name__ == "__main__":
    unittest.main()
