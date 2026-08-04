from __future__ import annotations

import copy
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

from docs.codex.audit_tools import (
    stage4_2r3c3t13s24d1r14r8_independent_forensics as independent,
)
from tsc_rzip_rllib.control import action_conditioned_history_response_model as model
from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification_370ms.json"


class Stage42R8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_frozen_config_and_self_test(self):
        r8._validate_config(copy.deepcopy(self.cfg), CONFIG)
        independent._validate(copy.deepcopy(self.cfg))
        result = r8.self_test(CONFIG)
        self.assertTrue(result["passed"])
        self.assertEqual(result["role_count_per_context"], 39)
        self.assertEqual(result["canonical_count_per_context"], 32)
        self.assertEqual(result["replacement_count_per_context"], 6)
        self.assertEqual(result["prospective_rollout_count"], 1248)
        self.assertFalse(result["physical_issue_time_centers_available_offline"])

    def test_timing_safety_partition_and_rl_mutations_fail_closed(self):
        changes = []
        changed = copy.deepcopy(self.cfg)
        changed["formal_timing_contract"]["normal_arrival_deadline_step"] = 26
        changes.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["controller_contract"]["maximum_online_cancel_incremental_linf"] = 0.25
        changes.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["pair_partitions"]["holdout"][0] = changed["pair_partitions"]["calibration"][0]
        changes.append(changed)
        changed = copy.deepcopy(self.cfg)
        changed["bc_dagger_or_rl_allowed"] = True
        changes.append(changed)
        for value in changes:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    r8._validate_config(value, CONFIG)

    def test_consumed_training_is_bookkeeping_not_a_new_source_phase(self):
        for pair in self.cfg["pair_partitions"]["consumed_training"]:
            self.assertEqual(r8._phase_for_pair(self.cfg, pair), "training")
        for pair in self.cfg["pair_partitions"]["training_extension"]:
            self.assertEqual(r8._phase_for_pair(self.cfg, pair), "training")

    def test_empty_issue10_preissue_interval_preserves_action_width(self):
        empty = r8._trace_action_matrix([], r8.PREFIX_END, r8.PREFIX_END)
        self.assertEqual(empty.shape, (0, r8.N_COILS))
        trace = [{"action_norm_tsc": [0.0] * r8.N_COILS}]
        populated = r8._trace_action_matrix(trace, 0, 1)
        self.assertEqual(populated.shape, (1, r8.N_COILS))

    def test_independent_finite_guard_accepts_metadata_and_rejects_nonfinite_plant_fields(self):
        row = {
            "R": 1.8,
            "Z": 0.0,
            "Ip": 100_000.0,
            "currents_a_tsc": [0.0] * r8.N_COILS,
            "wire_currents_a": [0.0, 1.0],
            "abnormal": False,
            "status": "valid string metadata",
        }
        currents = np.asarray([row["currents_a_tsc"]], dtype=float)
        self.assertTrue(independent._physical_trajectory_finite([row], currents, 0))
        changed = copy.deepcopy(row)
        changed["wire_currents_a"][0] = float("nan")
        self.assertFalse(independent._physical_trajectory_finite([changed], currents, 0))

    def test_reporting_repair_requires_explicit_resume(self):
        with self.assertRaisesRegex(ValueError, "requires explicit resume"):
            r8.execute(
                SimpleNamespace(),
                command="repair-training-raw-audit",
                backend="serial",
                resume=False,
            )
        with mock.patch.object(r8, "repair_training_raw_audit", return_value={"passed": True}) as repair:
            result = r8.execute(
                SimpleNamespace(),
                command="repair-training-raw-audit",
                backend="serial",
                resume=True,
            )
        self.assertTrue(result["passed"])
        repair.assert_called_once()

    def _blueprints(self):
        baselines, s21 = {}, {}
        groups = self.cfg["pair_partitions"]
        for partition_key, phase in (
            ("consumed_training", "training"),
            ("training_extension", "training"),
            ("calibration", "calibration"),
            ("holdout", "holdout"),
        ):
            for pair in groups[partition_key]:
                for history in r8.HISTORIES:
                    key = (pair, history)
                    baselines[key] = {
                        "experiment_id": f"source_{pair}_{history}",
                        "partition": phase,
                        "pair_id": pair,
                        "history_member": history,
                        "state_generation_experiment_id": f"state_{pair}_{history}",
                        "restart_snapshot_manifest_digest": f"digest_{pair}_{history}",
                        "restart_snapshot_dir": f"snapshot_{pair}_{history}",
                        "horizon_steps": 35,
                        "formal_horizon_steps": 35,
                        "target_R_offset_m": 0.0,
                        "target_Z_offset_m": 0.0,
                        "target_Ip_offset_A": 0.0,
                    }
                    s21[key] = {
                        "result": {"experiment_id": f"s21_{pair}_{history}"},
                        "sha256": "1" * 64,
                    }
        return baselines, s21

    def test_full_prospective_identity_and_kernel_coverage(self):
        specs = r8.build_specs(self.cfg, *self._blueprints())
        self.assertEqual(len(specs), 1248)
        self.assertEqual(len({row["experiment_id"] for row in specs}), 1248)
        self.assertEqual(
            {phase: sum(row["partition"] == phase for row in specs) for phase in r8.PHASES},
            {"training": 624, "calibration": 312, "holdout": 312},
        )
        contexts = {(row["pair_id"], row["history_member"]) for row in specs}
        self.assertEqual(len(contexts), 32)
        for context in contexts:
            rows = [row for row in specs if (row["pair_id"], row["history_member"]) == context]
            self.assertEqual(len(rows), 39)
            self.assertEqual(sum(row["d1r14r8_role"] == "baseline" for row in rows), 1)
            self.assertEqual(sum(row["d1r14r8_role"] == "canonical" for row in rows), 32)
            self.assertEqual(sum(row["d1r14r8_role"] == "replacement" for row in rows), 6)

    def test_kernel_adapter_strips_r8_labels_and_routes_by_schedule(self):
        specs = r8.build_specs(self.cfg, *self._blueprints())
        chosen = {
            (row["d1r14r8_role"], row["d1r14r8_issue_task_step"]): row
            for row in specs
            if row["history_member"] == "plus_first"
        }
        baseline = r8._kernel_spec(chosen[("baseline", -1)])
        issue10 = r8._kernel_spec(chosen[("canonical", 10)])
        issue14 = r8._kernel_spec(chosen[("canonical", 14)])
        replacement = r8._kernel_spec(chosen[("replacement", 14)])
        self.assertEqual(baseline["d1r14r4_role"], "baseline")
        self.assertEqual(issue10["d1r14r2_role"], "signed_probe")
        self.assertEqual(issue14["d1r14r4_role"], "signed_probe")
        self.assertEqual(replacement["d1r14r6_role"], "signed_probe")
        for adapted in (baseline, issue10, issue14, replacement):
            self.assertFalse(any(key.startswith("d1r14r8_") for key in adapted))
            self.assertNotIn("source_s21_baseline_experiment_id", adapted)

    def test_nested_outer_fold_reports_dynamic_training_pair_count(self):
        items = [
            {
                "response_id": f"r{index}",
                "pair_id": f"pair{index}",
                "response": [[0.0] * 5],
            }
            for index in range(12)
        ]
        candidate = model.Candidate(4, 1.0, 1e-3)
        fake_row = lambda item: {"response_id": item["response_id"]}
        with mock.patch.object(model, "select_candidate", return_value=(candidate, [])), mock.patch.object(
            model, "fit_model", return_value={}
        ), mock.patch.object(model, "predict_item", return_value=np.zeros((1, 5))), mock.patch.object(
            model, "prediction_row", side_effect=lambda item, _prediction, _cfg: fake_row(item)
        ):
            rows, folds = model.nested_outer_rows(items, self.cfg)
        self.assertEqual(len(rows), 12)
        self.assertEqual(len(folds), 12)
        self.assertEqual({row["training_pair_count"] for row in folds}, {11})

    def test_load_config_authenticates_d1r11_at_source_run_not_new_r8_run(self):
        source_d1r11 = ROOT / "source-d1r11"
        new_r8_run = ROOT / "new-r8-run"
        delegated = SimpleNamespace(paths=SimpleNamespace(stage_dir=source_d1r11 / "stage"))
        with mock.patch.object(r8.d1r11, "load_config", return_value=delegated) as load:
            ctx = r8.load_config(
                CONFIG,
                source_d1r11_run=source_d1r11,
                source_r2_run=ROOT / "r2",
                source_r4_run=ROOT / "r4",
                source_r6_run=ROOT / "r6",
                source_s21_run=ROOT / "s21",
                run_dir=new_r8_run,
            )
        self.assertEqual(load.call_args.kwargs["run_dir"], source_d1r11.resolve())
        self.assertEqual(load.call_args.kwargs["source_s21_run"], ROOT / "s21")
        self.assertEqual(ctx.source_d1r11_run, source_d1r11.resolve())
        self.assertEqual(ctx.paths.run_dir, new_r8_run.resolve())

    def test_phase_guard_and_tube_use_training_calibration_maximum(self):
        ctx = SimpleNamespace(paths=SimpleNamespace(state=Path("unused"), manifest=Path("unused")))
        with mock.patch.object(r8, "_read_json", return_value={"phase_status": "wrong", "finished": False}):
            with self.assertRaises(ValueError):
                r8._require_phase(ctx, "offline_ready")
        tube = r8._combined_tube(
            [0.01, 0.02, 0.03, 0.04, 0.05],
            [0.02, 0.01, 0.04, 0.03, 0.06],
            self.cfg,
        )
        self.assertEqual(
            tube["componentwise_maximum_absolute_scaled_error"],
            [0.02, 0.02, 0.04, 0.04, 0.06],
        )


if __name__ == "__main__":
    unittest.main()
