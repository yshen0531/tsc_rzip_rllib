from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import types
import unittest
from unittest import mock

import numpy as np

if sys.platform == "win32":
    try:
        import resource  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        resource = types.ModuleType("resource")
        resource.RLIMIT_NOFILE = 7
        resource.RLIMIT_CORE = 4
        resource.getrlimit = lambda _which: (65536, 65536)
        resource.setrlimit = lambda _which, _limits: None
        sys.modules["resource"] = resource

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign as s21,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "stage4_2r3c3t13s21_cumulative_exact_card15_pooled_observer_campaign_370ms.json"


class Stage4R3C3T13S21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_validates(self):
        s21._validate_config(copy.deepcopy(self.config))

    def test_split_is_disjoint_and_complete(self):
        assignment = s21._pair_partition_map(self.config)
        self.assertEqual(len(assignment), 20)
        self.assertEqual(sum(value[0] == "training" for value in assignment.values()), 12)
        self.assertEqual(sum(value[0] == "calibration" for value in assignment.values()), 4)
        self.assertEqual(sum(value[0] == "holdout" for value in assignment.values()), 4)

    def test_holdout_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["split"]["holdout"][0]["regime"] = "A"
        with self.assertRaises(ValueError):
            s21._validate_config(cfg)

    def test_tube_multiplier_mutation_fails_closed(self):
        cfg = copy.deepcopy(self.config)
        cfg["pooled_model"]["tube_multiplier"] = 4.01
        with self.assertRaises(ValueError):
            s21._validate_config(cfg)

    def test_s19_source_uses_canonical_frozen_inventory_digest(self):
        self.assertEqual(
            self.config["source_s19_development"]["raw_inventory_digest"],
            "3a2a468a92ea656b240280125ebac9b4e947d14bc3beb8e61a0fcdd82d1e01da",
        )
        cfg = copy.deepcopy(self.config)
        cfg["source_s19_development"]["raw_inventory_digest"] = (
            "dc31ee4be1159636cdf2d64638345f639ac0006d70d99862d7ce7af7774cd817"
        )
        with self.assertRaises(ValueError):
            s21._validate_config(cfg)

    def test_s20_forensic_source_is_frozen(self):
        self.assertEqual(
            self.config["source_s20_forensics"]["full_forensic_sha256"],
            "8a94fa842ab49a466ef3bbce07e248adb582f5abd461dca56a7bc81a1d39f890",
        )
        cfg = copy.deepcopy(self.config)
        cfg["source_s20_forensics"]["raw_inventory_digest"] = "0" * 64
        with self.assertRaises(ValueError):
            s21._validate_config(cfg)

    def test_rl_or_expert_data_mutation_fails_closed(self):
        for key in ("bc_dagger_or_rl_allowed", "probe_trajectories_allowed_in_expert_dataset"):
            cfg = copy.deepcopy(self.config)
            cfg[key] = True
            with self.assertRaises(ValueError):
                s21._validate_config(cfg)

    def _source_contexts(self):
        rows = []
        for pair in s21._pair_partition_map(self.config):
            for member in ("plus_first", "minus_first"):
                rows.append({
                    "pair_id": pair,
                    "history_member": member,
                    "state_generation_experiment_id": f"state-{pair}-{member}",
                    "restart_snapshot_dir": f"/server/snapshots/{pair}/{member}",
                    "restart_snapshot_manifest_digest": f"digest-{pair}-{member}",
                })
        return rows

    def _fake_context(self):
        base = SimpleNamespace(
            base_ctx=object(),
            cfg={
                "active_calibration": {
                    "response_issue_step": 10,
                    "response_cancel_step": 11,
                    "response_first_effect_state": 11,
                    "response_cancel_effect_state": 12,
                }
            },
        )
        return SimpleNamespace(cfg=copy.deepcopy(self.config), base_ctx=base)

    def test_context_table_has_frozen_partition_counts(self):
        with mock.patch.object(s21.s13, "build_context_table", return_value=self._source_contexts()):
            table = s21.build_context_table(self._fake_context())
        self.assertEqual(len(table), 40)
        self.assertEqual(
            {name: sum(row["partition"] == name for row in table) for name in ("training", "calibration", "holdout")},
            {"training": 24, "calibration": 8, "holdout": 8},
        )

    def test_spec_matrix_is_360_and_partitioned(self):
        context = self._fake_context()
        templates = {
            ("nominal", 0, 1.0): {},
            ("nominal", 2, 0.9): {},
            ("RZ_p10_m10", 0, 1.0): {},
            ("RZ_p10_m10", 2, 0.9): {},
        }
        with mock.patch.object(s21.s13, "build_context_table", return_value=self._source_contexts()):
            table = s21.build_context_table(context)
        with mock.patch.object(s21.s13, "_source_templates", return_value=templates), mock.patch.object(
            s21.s13, "_formal_horizon", side_effect=lambda slew: 37 if slew == 0.9 else 35
        ):
            specs = s21.build_specs(context, table)
        self.assertEqual(len(specs), 360)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 360)
        self.assertEqual(len(s21._partition_specs(specs, "training", baseline=True)), 24)
        self.assertEqual(len(s21._partition_specs(specs, "training", baseline=False)), 192)
        self.assertTrue(all(not row["probe_trajectory_allowed_in_expert_dataset"] for row in specs))

    def _causal_results(self):
        basis_fields = np.zeros((4, 14), dtype=float)
        basis_fields[:, :4] = np.eye(4) * 0.1
        coordinate = np.asarray([0.5, -0.25, 0.75, -0.5])
        signed = basis_fields.T @ coordinate
        turns = np.asarray([100.0] * 14)
        grid_a = 1e-6 * 1000.0 / turns
        center_fields = ["1.000E-01"] * 14
        center_target = np.asarray([float(field) * 10.0 for field in center_fields])
        nominal = center_target - 2.0 * grid_a
        prediction = {
            "uncertainty_radius_grid_units_tsc": [1.0] * 14,
            "bias_grid_units_tsc": [2.0] * 14,
            "output_grid_kAt": 1e-6,
            "readback_lower_a_tsc": (nominal - grid_a).tolist(),
            "readback_upper_a_tsc": (nominal + grid_a).tolist(),
        }
        trace = []
        calibration_inputs = [
            [1.0, 0.0, 0.0, 0.0], [-1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, -1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, -1.0],
        ]
        for index in range(11):
            trace.append({
                "r3c3t13s16_fixed_basis_delta_field_kAt_tsc": basis_fields.tolist(),
                "r3c3t13s9_signed_issue_delta_kAt_tsc": signed.tolist(),
                "r3c3t13s9_actuator_prediction": prediction,
                "r3c3t13s9_center_card15_fields": center_fields,
                "r3c3t13s21_partition_label_used": False,
                "r3c3t13s21_dynamic_input_coordinate": (
                    calibration_inputs[index] if index < 8 else []
                ),
            })
        baseline_trajectory = []
        result_trajectory = []
        for index in range(12):
            base = {"R": 1.0 + 1e-4 * index, "Z": -0.2 + 2e-4 * index, "Ip": 1e6 + index}
            probe = dict(base)
            if index == 11:
                probe.update({"R": base["R"] + 1e-5, "Z": base["Z"] - 2e-5, "Ip": base["Ip"] + 3.0})
            baseline_trajectory.append(base)
            result_trajectory.append(probe)
        spec = {
            "pair_id": "pair", "history_member": "plus_first", "partition": "training",
            "r3c3_probe_issue_step": 10, "r3c3_probe_first_effect_state": 11,
        }
        baseline = {"experiment_id": "baseline", "trajectory": baseline_trajectory, "spec": spec}
        result = {
            "experiment_id": "probe", "trajectory": result_trajectory,
            "controller_trace": trace, "spec": spec,
        }
        payload = {"env_cfg": {"turns_display_order": [100.0] * 14}}
        return result, baseline, payload

    def test_causal_row_uses_same_trajectory_features_only(self):
        result, baseline, payload = self._causal_results()
        row = s21._causal_row(result, baseline, payload, self.config)
        self.assertEqual(len(row["feature"]), 9)
        self.assertEqual(len(row["feature_radius"]), 9)
        self.assertEqual(row["forbidden_predictor_input_count"], 0)
        self.assertEqual(row["dynamic_design_rank"], 8)

    def test_dynamic_exact_target_repairs_decimal_exponent_boundary(self):
        centers = [" 0.000E+00"] * 14
        centers[8] = "-9.904E-01"
        desired = [Decimal("0")] * 14
        desired[8] = Decimal("-0.016")
        targets, actual, _ = s21._dynamic_exact_target(
            centers, desired, search_radius=16
        )
        self.assertEqual(targets[8], "-1.006E+00")
        self.assertEqual(actual[8], Decimal("-0.0156"))

    def test_cumulative_exact_target_reproduces_failed_s20_closure(self):
        pre_net = [
            Decimal(value) for value in (
                "0.0", "0.01", "0.04", "0.02", "0.02", "0.02", "0.02",
                "0.03", "0.0004", "0.024", "0.033", "0.02", "0.058", "0.048",
            )
        ]
        expected = (
            "-3.931E+01", "-5.052E+01", "-4.824E+01", "-3.391E+01",
            "-4.188E+01", "-4.259E+01", "-3.352E+01", "-3.049E+01",
            "-9.224E-01", "1.487E+00 ", "-7.609E+00", "-1.251E+01",
            "-7.522E+00", "-6.702E+00",
        )
        centers = tuple(
            s21.s16.s9.format_number(
                float(s21.s16.s9._decimal_field(target) + running)
            )
            for target, running in zip(expected, pre_net)
        )
        targets, actual, counts = s21._cumulative_exact_target(centers, pre_net)
        self.assertEqual(targets, expected)
        self.assertEqual(actual, tuple(-value for value in pre_net))
        self.assertTrue(all(before + delta == 0 for before, delta in zip(pre_net, actual)))
        self.assertEqual(len(counts), 14)

    def test_dynamic_design_accepts_recorded_coordinates(self):
        rows = [
            [0.975, 0.0, 0.0, 0.0], [-0.975, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, -1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, -1.0],
        ]
        trace = [
            {"r3c3t13s21_dynamic_input_coordinate": row} for row in rows
        ] + [{}, {}]
        design, audit = s21._dynamic_design(trace, self.config)
        self.assertEqual(design.shape, (10, 8))
        self.assertEqual(audit["dynamic_design_rank"], 8)
        self.assertLessEqual(audit["dynamic_design_condition"], 4.0)

    def _synthetic_rows(self, pair_count, rows_per_pair, partition):
        rng = np.random.default_rng(19 + pair_count)
        weights = rng.normal(size=(9, 5)) * np.asarray([1e-5, 1e-5, 1e-4, 1e-4, 1.0])
        output = []
        for pair in range(pair_count):
            for index in range(rows_per_pair):
                feature = rng.normal(size=9)
                response = feature @ weights
                output.append({
                    "experiment_id": f"{partition}-{pair:02d}-{index:02d}",
                    "pair_id": f"pair-{pair:02d}", "history_member": "plus_first",
                    "partition": partition, "feature": feature.tolist(),
                    "feature_radius": (np.ones(9) * 1e-10).tolist(),
                    "actual_response": response.tolist(),
                    "forbidden_predictor_input_count": 0,
                })
        return output

    def test_training_artifact_freezes_before_calibration(self):
        rows = self._synthetic_rows(12, 16, "training")
        ctx = SimpleNamespace(cfg=self.config)
        with mock.patch.object(s21, "_extract_rows", return_value=rows):
            audit, artifact = s21._build_training_artifact(ctx, [],)
        self.assertTrue(audit["passed"])
        self.assertTrue(artifact["passed"])
        self.assertEqual(artifact["calibration_outcome_access_count_before_model_hash"], 0)
        self.assertEqual(artifact["holdout_outcome_access_count_before_model_hash"], 0)

    def test_evaluate_rows_enforces_point_tube_and_caps(self):
        rows = self._synthetic_rows(4, 16, "calibration")
        x = np.asarray([row["feature"] for row in rows])
        y = np.asarray([row["actual_response"] for row in rows])
        scales = np.asarray(self.config["causal_model"]["response_scales"])
        model = s21.s18._fit_model(x, y, 1e-8, scales, 1e-12)
        evaluated, summary = s21._evaluate_rows(
            SimpleNamespace(cfg=self.config), rows, model, np.ones(5) * 1e-6
        )
        self.assertEqual(len(evaluated), 64)
        self.assertTrue(summary["passed"])

    def test_calibration_freezes_fixed_residual_before_holdout(self):
        training_rows = self._synthetic_rows(12, 16, "training")
        ctx = SimpleNamespace(cfg=self.config, paths=SimpleNamespace(
            model=ROOT / ".codex_tmp" / "not_opened_by_unit_test"
        ))
        with mock.patch.object(s21, "_extract_rows", return_value=training_rows):
            _, training = s21._build_training_artifact(ctx, [])
        model = s21.s18._deserialize_model(training["model"])
        rng = np.random.default_rng(1919)
        features = rng.normal(size=(64, 9))
        scales = np.asarray(self.config["causal_model"]["response_scales"])
        truth = s21.s18._predict(model, features, scales)
        calibration_rows = []
        for index, (feature, response) in enumerate(zip(features, truth)):
            calibration_rows.append({
                "experiment_id": f"calibration-{index:03d}",
                "pair_id": f"pair-{index // 16:02d}", "history_member": "plus_first",
                "partition": "calibration", "feature": feature.tolist(),
                "feature_radius": (np.ones(9) * 1e-10).tolist(),
                "actual_response": response.tolist(),
                "forbidden_predictor_input_count": 0,
            })
        with mock.patch.object(s21, "_extract_rows", return_value=calibration_rows), mock.patch.object(
            s21, "_sha256", return_value="frozen-model-sha"
        ):
            audit, tube = s21._build_calibration_artifact(ctx, [], training)
        self.assertTrue(audit["passed"])
        self.assertTrue(tube["passed"])
        self.assertEqual(tube["holdout_outcome_access_count_before_tube_hash"], 0)
        self.assertTrue(np.all(
            np.asarray(tube["calibrated_componentwise_residual"])
            >= np.asarray(training["training_maximum_oof_residual"])
        ))

    def test_point_gate_cannot_be_hidden_by_a_wide_tube(self):
        rows = self._synthetic_rows(4, 16, "holdout")
        x = np.asarray([row["feature"] for row in rows])
        y = np.asarray([row["actual_response"] for row in rows])
        scales = np.asarray(self.config["causal_model"]["response_scales"])
        model = s21.s18._fit_model(x, y, 1e-8, scales, 1e-12)
        rows[0]["actual_response"] = (np.asarray(rows[0]["actual_response"]) + 0.2 * scales).tolist()
        evaluated, summary = s21._evaluate_rows(
            SimpleNamespace(cfg=self.config), rows, model, np.asarray([1e-3, 1e-3, 1e-3, 1e-3, 10.0])
        )
        self.assertFalse(evaluated[0]["point_pass"])
        self.assertFalse(summary["passed"])

    def test_phase_guard_fails_closed(self):
        ctx = SimpleNamespace(paths=SimpleNamespace(state=Path("unused-state.json")))
        with mock.patch.object(s21, "_read_json", return_value={"phase_status": "offline_ready", "finished": False}):
            with self.assertRaises(ValueError):
                s21._require_phase(ctx, "training_model_frozen")

    def test_failed_baseline_sets_terminal_phase_status(self):
        ctx = SimpleNamespace(paths=SimpleNamespace(
            raw=ROOT / ".codex_tmp" / "unused-s21-raw",
            analysis=ROOT / ".codex_tmp" / "unused-s21-analysis",
        ))
        with mock.patch.object(s21, "_require_phase"), mock.patch.object(
            s21, "_all_specs", return_value=[]
        ), mock.patch.object(
            s21, "_partition_specs", side_effect=[[], []]
        ), mock.patch.object(
            s21, "evaluate_specs", return_value={"passed": False}
        ), mock.patch.object(s21, "_write_json"), mock.patch.object(
            s21, "_set_state"
        ) as set_state:
            result = s21.run_baseline(
                ctx, "training", backend="serial", resume=False
            )
        self.assertFalse(result["passed"])
        self.assertEqual(
            set_state.call_args.kwargs["phase_status"], "training_baseline_failed"
        )

    def test_self_test_runs_without_tsc(self):
        result = s21.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertFalse(result["real_tsc_executed"])
        self.assertEqual(result["new_tsc_or_plant_step_count"], 0)

    def test_cli_source_names_translate_to_load_config_contract(self):
        cli_names = (
            "source_stage4_2r3b_run", "source_stage4_2r3c3_run",
            "source_stage4_2r3c3_bank_dir", "source_stage4_2r3c3t1_run",
            "source_stage4_2r3c3t1_audit_dir", "source_stage4_2r3c3t3_controller_bank",
            "q1_run", "q2_run", "q1_audit", "q2_audit", "r3b_server_audit",
            "r3b_snapshot_checks", "run_dir",
        )
        args = SimpleNamespace(**{name: Path(name) for name in cli_names})
        translated = s21._cli_source_kwargs(args)
        self.assertEqual(len(translated), 13)
        self.assertEqual(
            set(translated),
            {
                "source_stage42r3b_run", "source_stage42r3c3_run",
                "source_stage42r3c3_bank_dir", "source_stage42r3c3t1_run",
                "source_stage42r3c3t1_audit_dir", "source_stage42r3c3t3_controller_bank",
                "q1_run", "q2_run", "q1_audit", "q2_audit", "r3b_server_audit",
                "r3b_snapshot_checks", "run_dir",
            },
        )
        self.assertEqual(
            translated["source_stage42r3b_run"], Path("source_stage4_2r3b_run")
        )

    def test_payload_reuses_complete_s16_context_adapter(self):
        t11_base = SimpleNamespace(source_ctx=SimpleNamespace(source_ctx=object()), cfg={})
        t11_context = SimpleNamespace(base_ctx=t11_base)
        s9_context = SimpleNamespace(base_ctx=t11_context)
        s13_context = SimpleNamespace(base_ctx=s9_context)
        s16_context = SimpleNamespace(base_ctx=s13_context)
        context = SimpleNamespace(
            base_ctx=s16_context,
            paths=SimpleNamespace(variants=Path("unused-variants")),
        )
        spec = {
            "experiment_id": "payload-contract",
            "restart_snapshot_dir": "/server/snapshot",
            "restart_snapshot_manifest_digest": "snapshot-digest",
        }

        def bottom_payload(inner_context, *, spec):
            self.assertIs(inner_context.base_ctx, t11_context)
            self.assertEqual(spec["experiment_id"], "payload-contract")
            return {}

        with mock.patch.object(
            s21.s16.s9, "_control_payload", side_effect=bottom_payload
        ), mock.patch.object(s21.s13, "_write_json"), mock.patch.object(
            s21.s16, "_write_json"
        ), mock.patch.object(s21, "_write_json"):
            payload = s21._payload(context, spec)
        self.assertEqual(
            payload["stage4_2r3c3t13s21_snapshot_manifest_digest"], "snapshot-digest"
        )
        self.assertFalse(
            payload["stage4_2r3c3t13s21_pair_history_partition_label_available_to_controller"]
        )


if __name__ == "__main__":
    unittest.main()
