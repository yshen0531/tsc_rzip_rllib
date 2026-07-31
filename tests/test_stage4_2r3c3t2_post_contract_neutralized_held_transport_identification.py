from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t2_post_contract_neutralized_held_transport_identification
    as t2,
)


class Stage42R3C3T2DesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(t2.__file__).resolve().parents[2]
        cls.config_path = (
            cls.root
            / "configs"
            / "stage4_2r3c3t2_post_contract_neutralized_held_transport_identification_500ms.json"
        )
        cls.overlay = json.loads(
            cls.config_path.read_text(encoding="utf-8")
        )

    def test_resolved_identity_matrix_and_timing_are_frozen(self) -> None:
        cfg, base_path = t2._resolved_config(self.config_path)
        self.assertTrue(base_path.is_file())
        self.assertEqual(cfg["stage"], "Stage4.2R3c3T2")
        self.assertEqual(cfg["design_revision"], 2)
        self.assertEqual(
            cfg["controller_revision"],
            "post_contract_neutralized_held_transport_probe_v42r3c3t2_v2",
        )
        self.assertEqual(
            cfg["package_revision"],
            "r42r3c3t2_post_contract_held_transport_identification_v2h2",
        )
        self.assertEqual(cfg["control_matrix"]["expected_rollouts"], 160)
        self.assertEqual(
            cfg["control_matrix"]["expected_extended_baseline_rollouts"],
            32,
        )
        self.assertEqual(
            cfg["control_matrix"]["expected_signed_probe_rollouts"], 128
        )
        self.assertEqual(
            cfg["identification_probe"]["observation_horizon_steps"], 50
        )
        self.assertEqual(
            cfg["formal_timing_contract"]["normal"][
                "arrival_deadline_step"
            ],
            25,
        )
        self.assertEqual(
            cfg["formal_timing_contract"]["normal"]["hold_through_step"],
            35,
        )
        self.assertEqual(
            cfg["formal_timing_contract"]["weak"][
                "arrival_deadline_step"
            ],
            27,
        )
        self.assertEqual(
            cfg["formal_timing_contract"]["weak"]["hold_through_step"],
            37,
        )
        self.assertFalse(cfg["independent_long_hold_validated"])

    def test_schedule_is_delay_aware_zero_net_and_post_contract(self) -> None:
        cfg, _ = t2._resolved_config(self.config_path)
        amplitudes = cfg["identification_probe"][
            "physical_mode_amplitude"
        ]
        for basis in cfg["identification_probe"]["basis"]:
            for delay, expected in (
                (
                    0,
                    [2, 3, 4, 5, 6, 7, 38, 39, 40, 41, 42, 43],
                ),
                (
                    2,
                    [0, 1, 2, 3, 4, 5, 36, 37, 38, 39, 40, 41],
                ),
            ):
                for sign in (-1, 1):
                    schedule = t2._probe_schedule(
                        basis=basis,
                        actual_delay=delay,
                        sign=sign,
                        amplitude_by_mode=amplitudes,
                    )
                    self.assertEqual(sorted(schedule), expected)
                    self.assertTrue(
                        np.allclose(
                            np.sum(
                                np.stack(list(schedule.values())), axis=0
                            ),
                            np.zeros(t2.N_MODES),
                            rtol=0.0,
                            atol=1.0e-12,
                        )
                    )
                    negative_effects = sorted(
                        step + delay + 1
                        for step, value in schedule.items()
                        if float(value[int(basis["mode"])]) * sign < 0
                    )
                    self.assertEqual(
                        negative_effects, [39, 40, 41, 42, 43, 44]
                    )

    def test_self_test_is_exact(self) -> None:
        result = t2.self_test()
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["first_negative_physical_effect_state"], 39
        )
        self.assertEqual(result["formal_normal_hold_through_step"], 35)
        self.assertEqual(result["formal_weak_hold_through_step"], 37)
        self.assertFalse(
            result["observation_horizon_is_long_hold_validation"]
        )

    @staticmethod
    def _source_templates() -> list[dict]:
        templates = []
        for pair in ("p5_q1", "p5_q2", "p9_q1", "p9_q2"):
            for history in ("minus_first", "plus_first"):
                for target in ("RZ_p10_m10", "nominal"):
                    for delay, slew in ((0, 1.0), (2, 0.9)):
                        templates.append(
                            {
                                "pair_id": pair,
                                "history_member": history,
                                "target_id": target,
                                "action_delay_steps": delay,
                                "slew_scale": slew,
                                "horizon_steps": 35
                                if slew == 1.0
                                else 37,
                                "baseline_experiment_id": (
                                    f"baseline_{pair}_{history}_{target}_"
                                    f"{delay}_{slew}"
                                ),
                                "restart_snapshot_dir": "/server/snapshot",
                                "restart_snapshot_manifest_digest": "a"
                                * 64,
                                "state_generation_experiment_id": (
                                    f"state_{pair}_{history}"
                                ),
                            }
                        )
        return templates

    def test_spec_matrix_has_one_baseline_and_four_probes_per_context(
        self,
    ) -> None:
        cfg, base = t2._resolved_config(self.config_path)
        ctx = t2.Stage42R3C3T2Context(
            cfg=cfg,
            base_config_path=base,
            source_ctx=SimpleNamespace(),
            source_t1_run=Path("/server/t1"),
            source_t1_audit_dir=Path("/server/audit"),
            source_t1_fingerprint={"raw_inventory_digest": "b" * 64},
            paths=t2._paths(self.root / ".codex_tmp" / "unused_t2"),
        )
        templates = self._source_templates()
        with mock.patch.object(
            t2.t1, "build_control_specs", return_value=templates
        ):
            specs = t2.build_control_specs(ctx, [])
        self.assertEqual(len(specs), 160)
        self.assertEqual(
            len({spec["experiment_id"] for spec in specs}), 160
        )
        grouped = {}
        for spec in specs:
            grouped.setdefault(t2._context_key(spec), []).append(spec)
            self.assertEqual(spec["horizon_steps"], 50)
            self.assertEqual(
                spec["formal_horizon_steps"],
                35 if spec["slew_scale"] == 1.0 else 37,
            )
        self.assertEqual(len(grouped), 32)
        for rows in grouped.values():
            self.assertEqual(len(rows), 5)
            baseline = [
                row
                for row in rows
                if row["r3c3_probe_id"] == t2.BASELINE_PROBE_ID
            ]
            self.assertEqual(len(baseline), 1)
            self.assertEqual(baseline[0]["r3c3_probe_sign"], 0)
            self.assertEqual(
                baseline[0]["r3c3_probe_delta_by_task_issue_step"], {}
            )

    def test_config_rejects_matrix_and_timing_changes(self) -> None:
        cfg, _ = t2._resolved_config(self.config_path)
        changed = copy.deepcopy(cfg)
        changed["control_matrix"]["expected_rollouts"] = 159
        with self.assertRaisesRegex(ValueError, "matrix"):
            t2._validate_config(changed)
        changed = copy.deepcopy(cfg)
        changed["formal_timing_contract"]["weak"][
            "arrival_deadline_step"
        ] = 28
        with self.assertRaisesRegex(ValueError, "formal contract"):
            t2._validate_config(changed)

    def test_phase_validator_accepts_baseline_and_signed_trace(self) -> None:
        def trace(schedule):
            rows = []
            for step in range(50):
                expected = schedule.get(step, np.zeros(t2.N_MODES))
                issued = step in schedule
                rows.append(
                    {
                        "task_step": step,
                        "r3c3_probe_requested_delta": expected.tolist(),
                        "r3c3_probe_applied_desired_delta": (
                            expected.tolist()
                        ),
                        "r3c3_probe_issued": issued,
                        "r3c3t2_identification_only": True,
                        "solver_success": True,
                    }
                )
            return rows

        base_result = {
            "spec": {
                "r3c3_probe_id": t2.BASELINE_PROBE_ID,
                "r3c3_probe_delta_by_task_issue_step": {},
            },
            "controller_trace": trace({}),
        }
        with mock.patch.object(
            t2.t1.r3c1,
            "_phase_trace_valid",
            return_value={"passed": True},
        ):
            self.assertTrue(t2._phase_trace_valid(base_result)["passed"])
            schedule = t2._probe_schedule(
                basis={
                    "mode": 0,
                    "positive_effect_states": [3, 4, 5, 6, 7, 8],
                    "negative_effect_states": [39, 40, 41, 42, 43, 44],
                },
                actual_delay=2,
                sign=1,
                amplitude_by_mode=[0.006, 0.0075, 0.0],
            )
            signed_result = {
                "spec": {
                    "r3c3_probe_id": "held_transport_mode0",
                    "r3c3_probe_delta_by_task_issue_step": {
                        str(step): value.tolist()
                        for step, value in schedule.items()
                    },
                },
                "controller_trace": trace(schedule),
            }
            self.assertTrue(
                t2._phase_trace_valid(signed_result)["passed"]
            )

    def test_formal_prefix_truncates_the_observation_tail(self) -> None:
        result = {
            "spec": {
                "formal_horizon_steps": 35,
                "horizon_steps": 50,
            },
            "trajectory": [{"step": index} for index in range(51)],
            "controller_trace": [{"step": index} for index in range(50)],
        }
        ctx = SimpleNamespace(source_ctx=SimpleNamespace(base_ctx="base"))

        def fake_formal(source_ctx, truncated):
            self.assertEqual(source_ctx, "base")
            self.assertEqual(len(truncated["trajectory"]), 36)
            self.assertEqual(len(truncated["controller_trace"]), 35)
            self.assertEqual(truncated["spec"]["horizon_steps"], 35)
            return {"passed": True}

        truncated = t2._formal_prefix_result(result)
        self.assertEqual(len(truncated["trajectory"]), 36)
        self.assertEqual(len(truncated["controller_trace"]), 35)
        self.assertEqual(truncated["spec"]["horizon_steps"], 35)
        self.assertEqual(len(result["trajectory"]), 51)
        self.assertEqual(result["spec"]["horizon_steps"], 50)
        with mock.patch.object(
            t2.t1.r3c3, "_formal_metrics", side_effect=fake_formal
        ):
            self.assertEqual(
                t2._formal_prefix_metrics(ctx, result), {"passed": True}
            )

    def test_offline_raw_gate_distinguishes_first_run_and_resume(self) -> None:
        gate = t2._offline_raw_directory_gate
        self.assertTrue(
            gate(raw_count=0, expected=160, allow_existing_raw=False)
        )
        self.assertFalse(
            gate(raw_count=1, expected=160, allow_existing_raw=False)
        )
        self.assertTrue(
            gate(raw_count=0, expected=160, allow_existing_raw=True)
        )
        self.assertTrue(
            gate(raw_count=160, expected=160, allow_existing_raw=True)
        )
        self.assertFalse(
            gate(raw_count=161, expected=160, allow_existing_raw=True)
        )

    def test_payload_overrides_inherited_formal_episode_horizon(self) -> None:
        ctx = SimpleNamespace(
            source_ctx=SimpleNamespace(source_ctx="source"),
            cfg={"storage": {}},
            paths=SimpleNamespace(variants=Path("/server/variants")),
        )
        spec = {
            "experiment_id": "test_horizon",
            "restart_snapshot_dir": "/server/snapshot",
            "restart_snapshot_manifest_digest": "a" * 64,
        }
        inherited = {
            "train_cfg": {
                "episode": {"max_episode_steps": 35},
                "env_config": "/server/variants/env_test_horizon.json",
            },
            "stage4_1r4_horizon_steps": 35,
        }
        writes = {}

        def record(path, value):
            writes[Path(path).name] = copy.deepcopy(value)

        with mock.patch.object(
            t2.t1.r3c3,
            "_control_payload",
            return_value=copy.deepcopy(inherited),
        ), mock.patch.object(
            t2.t1.r3c3,
            "atomic_write_json",
            side_effect=record,
        ):
            payload = t2._control_payload(ctx, spec=spec)
        self.assertEqual(
            payload["train_cfg"]["episode"]["max_episode_steps"], 50
        )
        self.assertEqual(payload["stage4_1r4_horizon_steps"], 50)
        self.assertEqual(
            writes["train_test_horizon.json"]["episode"][
                "max_episode_steps"
            ],
            50,
        )
        self.assertEqual(
            writes["payload_test_horizon.json"][
                "stage4_1r4_horizon_steps"
            ],
            50,
        )

    def test_t1_failed_source_authentication_is_exact(self) -> None:
        cfg, _ = t2._resolved_config(self.config_path)
        req = cfg["source_t1_requirements"]
        run = Path("/server") / req["required_run_name"]
        audit = Path("/server/t1_audit")
        manifest = {
            "stage": req["required_stage"],
            "controller_revision": req["required_controller_revision"],
            "package_revision": req["required_package_revision"],
        }
        state = {"finished": True, "primary_pass": False}
        server_audit = {
            "raw_and_manifest_integrity_passed": True,
            "control_raw_actual": req["required_raw_count"],
            "raw_inventory": {
                "digest": req["required_raw_inventory_digest"]
            },
            "control_summary": {
                "combined_condition_pass_count": (
                    req["required_combined_condition_pass_count"]
                ),
                "combined_condition_group_count": (
                    req["required_combined_condition_context_count"]
                ),
            },
            "runtime_package_fingerprint_digest": "f" * 64,
        }
        diagnostic = {
            "scale_summaries": [
                {
                    "optimistic_formal_pass_count": (
                        req["required_optimistic_formal_pass_count"]
                    ),
                    "failed_baseline_repair_count": (
                        req["required_failed_context_repair_count"]
                    ),
                }
            ]
        }

        def fake_read(path):
            name = Path(path).name
            if name == "stage4_2r3c3t1_manifest.json":
                return manifest
            if name == "stage4_2r3c3t1_state.json":
                return state
            if name == "stage4_2r3c3t1_server_audit.json":
                return server_audit
            if name.endswith("diagnostic_v2.json"):
                return diagnostic
            raise AssertionError(name)

        def fake_sha(path):
            name = Path(path).name
            if name == "stage4_2r3c3t1_server_audit.json":
                return req["required_server_audit_sha256"]
            if name.endswith("diagnostic_v2.json"):
                return req[
                    "required_corrected_six_basis_diagnostic_sha256"
                ]
            return "a" * 64

        with mock.patch.object(
            t2.t1.r3c3, "read_json", side_effect=fake_read
        ), mock.patch.object(t2, "_sha256", side_effect=fake_sha):
            fingerprint = t2._authenticate_t1_source(cfg, run, audit)
        self.assertFalse(fingerprint["primary_pass"])
        self.assertEqual(
            fingerprint["failure_class"],
            "identification_design_failure",
        )
        self.assertEqual(
            fingerprint["raw_inventory_digest"],
            req["required_raw_inventory_digest"],
        )

        server_audit["control_summary"][
            "combined_condition_group_count"
        ] = 31
        with mock.patch.object(
            t2.t1.r3c3, "read_json", side_effect=fake_read
        ), mock.patch.object(t2, "_sha256", side_effect=fake_sha):
            with self.assertRaisesRegex(ValueError, "authentication"):
                t2._authenticate_t1_source(cfg, run, audit)

    def test_resume_manifest_rejects_source_fingerprint_change(self) -> None:
        proposed = {
            "stage": t2.STAGE,
            "source_stage4_2r3c3t1_fingerprint": {
                "raw_inventory_digest": "a" * 64
            },
            "control_spec_digest": "b" * 64,
        }
        t2._validate_resume_manifest(copy.deepcopy(proposed), proposed)
        changed = copy.deepcopy(proposed)
        changed["source_stage4_2r3c3t1_fingerprint"][
            "raw_inventory_digest"
        ] = "c" * 64
        with self.assertRaisesRegex(
            ValueError,
            "source_stage4_2r3c3t1_fingerprint",
        ):
            t2._validate_resume_manifest(changed, proposed)


if __name__ == "__main__":
    unittest.main()
