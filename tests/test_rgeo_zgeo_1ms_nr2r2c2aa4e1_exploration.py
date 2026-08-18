from __future__ import annotations

import copy
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rgeo_zgeo_1ms_nr2r2c2aa4e1_single_successor_exploration.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E1 = load_module(
    "c2aa4e1_exploration", "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_exploration.py"
)
E1_INDEPENDENT = load_module(
    "c2aa4e1_independent", "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_independent.py"
)
E1_PACKAGE = load_module(
    "c2aa4e1_package", "scripts/rgeo_zgeo_1ms_nr2r2c2aa4e1_verify_package.py"
)


def synthetic_signal(record: dict) -> SimpleNamespace:
    return SimpleNamespace(
        boundary=SimpleNamespace(
            r_geo_m=float(record["r_geo_m"]), z_geo_m=float(record["z_geo_m"])
        ),
        limiter=SimpleNamespace(
            r_mid_m=float(record["r_mid_m"]),
            r_inner_m=float(record["r_inner_m"]),
            r_outer_m=float(record["r_outer_m"]),
        ),
        ip_a=float(record["ip_a"]),
    )


def synthetic_state(record: dict, *, abnormal: bool = False) -> dict:
    stored = copy.deepcopy(record)
    stored["reported_returncode"] = 0
    stored["reported_abnormal"] = abnormal
    stored["reported_done_reason"] = "synthetic abnormal" if abnormal else ""
    stored["reported_runtime_ok"] = not abnormal
    return {
        "record": stored,
        "signal": synthetic_signal(record),
        "currents_a_tsc": list(record["actual_current_a_tsc"]),
        "returncode": 0,
        "abnormal": abnormal,
        "done_reason": "synthetic abnormal" if abnormal else "",
    }


class FakeRunner:
    """No-TSC runner with separately observable attempts and gotsc entries."""

    instances: list["FakeRunner"] = []
    states: list[dict] = []
    fail_issue: int | None = None
    fail_before_gotsc = False
    abnormal_issue: int | None = None

    def __init__(self, *_args, **_kwargs) -> None:
        self.plant_advance_gotsc_calls = 0
        self.step_calls: list[np.ndarray] = []
        self.reset_calls = 0
        self.cleaned = False
        type(self).instances.append(self)

    def reset(self, *, episode_name: str) -> dict:
        self.reset_calls += 1
        self.episode_name = episode_name
        return copy.deepcopy(type(self).states[0])

    def step_current_a(self, target: np.ndarray) -> dict:
        issue = len(self.step_calls)
        self.step_calls.append(np.asarray(target, dtype=float).copy())
        if issue == type(self).fail_issue and type(self).fail_before_gotsc:
            raise RuntimeError("synthetic pre-gotsc failure")
        self.plant_advance_gotsc_calls += 1
        if issue == type(self).fail_issue:
            raise RuntimeError("synthetic post-gotsc failure")
        state = copy.deepcopy(type(self).states[issue + 1])
        if issue == type(self).abnormal_issue:
            state["abnormal"] = True
        return state

    def cleanup_runtime_workspace(self) -> None:
        self.cleaned = True


def fake_rollout_inputs(stage: dict):
    replay = json.loads(
        (ROOT / stage["evidence"]["a3_replay_0"]["path"]).read_text(encoding="utf-8")
    )
    cfg = SimpleNamespace(
        turns_tsc=np.asarray([480.0] * 8 + [200.0] * 2 + [100.0] * 4),
        min_current_a_tsc=np.asarray([-10_000.0] * 14),
        max_current_a_tsc=np.asarray([10_000.0] * 14),
        current_slew_a_per_ms=0.3,
    )
    q0 = E1.target_from_fields(
        replay["actions"][0]["expected_card15_fields"], cfg, "test.q0"
    )
    level1 = E1.target_from_fields(stage["level1_card15_fields"], cfg, "test.level1")
    level2 = E1.target_from_fields(stage["level2_card15_fields"], cfg, "test.level2")
    targets = (q0, level1) + (level2,) * 15

    reference = copy.deepcopy(replay)
    reference["actions"] = []
    previous = reference["states"][0]["active_command_decimal_a_tsc"]
    for issue, target in enumerate(targets[:16]):
        exact = E1.card15_target_decimal_a(target, cfg.turns_tsc, name=f"test.{issue}")
        maximum = E1.assert_exact_slew(previous, exact, name=f"test.{issue}")
        reference["actions"].append(E1._target_action(target, issue, maximum))
        previous = exact

    records = [copy.deepcopy(row) for row in reference["states"][:17]]
    state17 = copy.deepcopy(records[16])
    state17["time_ms"] = 1117
    state17["active_command_card15_fields"] = list(level2.card15_fields)
    state17["active_command_decimal_a_tsc"] = [
        str(value)
        for value in E1.card15_target_decimal_a(level2, cfg.turns_tsc, name="test.state17")
    ]
    records.append(state17)
    return cfg, reference, targets, records


def inside_repo_tmp() -> Path:
    path = ROOT / ".codex_tmp" / f"e1_test_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def git_blob_oid(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def build_synthetic_package(root: Path, tool_revision: str) -> tuple[str, str]:
    for relative in E1_PACKAGE.EXPECTED_PAYLOAD_FILES:
        source = ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    files = []
    for relative in E1_PACKAGE.EXPECTED_PAYLOAD_FILES:
        path = root / relative
        files.append({
            "path": relative,
            "role": E1_PACKAGE._expected_role(relative),
            "source_revision": E1_PACKAGE._expected_source_revision(
                relative, tool_revision
            ),
            "git_blob_oid": git_blob_oid(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    manifest = {
        "schema_version": E1_PACKAGE.MANIFEST_SCHEMA,
        "package_identity": E1_PACKAGE.PACKAGE_IDENTITY,
        "runtime_revision": E1_PACKAGE.RUNTIME_REVISION,
        "package_tool_revision": tool_revision,
        "stage_config_path": E1_PACKAGE.STAGE_CONFIG_PATH,
        "stage_config_sha256": E1_PACKAGE.STAGE_CONFIG_SHA256,
        "manifest_path": E1_PACKAGE.MANIFEST_PATH,
        "checksum_path": E1_PACKAGE.CHECKSUM_PATH,
        "payload_file_count": len(E1_PACKAGE.EXPECTED_PAYLOAD_FILES),
        "checksum_entry_count": len(E1_PACKAGE.EXPECTED_CHECKSUM_FILES),
        "checksum_self_included": False,
        "zero_plant_package_verification": True,
        "files": files,
    }
    manifest_path = root / E1_PACKAGE.MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    checksums = {
        E1_PACKAGE.MANIFEST_PATH: sha256(manifest_path),
        **{relative: sha256(root / relative)
           for relative in E1_PACKAGE.EXPECTED_PAYLOAD_FILES},
    }
    checksum_path = root / E1_PACKAGE.CHECKSUM_PATH
    checksum_path.write_text(
        "".join(
            f"{checksums[relative]}  {relative}\n"
            for relative in E1_PACKAGE.EXPECTED_CHECKSUM_FILES
        ),
        encoding="utf-8",
        newline="\n",
    )
    return sha256(manifest_path), sha256(checksum_path)


def run_package_verifier(
    root: Path,
    manifest_sha256: str,
    checksum_sha256: str,
    tool_revision: str,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            str(root / E1_PACKAGE.VERIFIER_PATH),
            "--repo-root", str(root),
            "--expected-manifest-sha256", manifest_sha256,
            "--expected-checksum-sha256", checksum_sha256,
            "--expected-package-tool-revision", tool_revision,
        ],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed, json.loads(completed.stdout)


class C2AA4E1FrozenContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_one_reset_attempt_and_successor_budget_is_machine_readable(self) -> None:
        self.assertEqual(self.stage["rollouts"], 1)
        self.assertEqual(self.stage["maximum_reset_calls"], 1)
        self.assertEqual(self.stage["maximum_plant_advances"], 17)
        self.assertEqual(self.stage["maximum_advance_attempts"], 17)
        self.assertEqual(self.stage["maximum_plant_advance_gotsc_calls"], 17)
        self.assertEqual(self.stage["retry_after_any_advance_attempt"], "forbidden")
        self.assertEqual(self.stage["completed_execution_required_state_count"], 18)

    def test_schedule_has_one_and_only_one_unknown_successor(self) -> None:
        covered = [
            (step, row["level"])
            for row in self.stage["schedule"]
            for step in range(row["first_step"], row["last_step"] + 1)
        ]
        self.assertEqual([step for step, _ in covered], list(range(17)))
        self.assertEqual(dict(covered)[0], "q0")
        self.assertEqual(dict(covered)[1], "level1")
        self.assertTrue(all(dict(covered)[step] == "level2" for step in range(2, 17)))
        self.assertEqual(self.stage["known_prefix_last_issue_step"], 15)
        self.assertEqual(self.stage["known_prefix_last_state_index"], 16)
        self.assertEqual(self.stage["empirical_exploration_issue_step"], 16)
        self.assertEqual(self.stage["empirical_exploration_effect_state_index"], 17)
        self.assertEqual(self.stage["empirical_exploration_level2_effect_age"], 15)
        self.assertEqual(self.stage["unknown_successor_count"], 1)

    def test_level2_is_exactly_twice_the_level1_q0_offset(self) -> None:
        a3 = json.loads((ROOT / self.stage["evidence"]["a3_replay_0"]["path"])
                        .read_text(encoding="utf-8"))
        q0 = a3["actions"][0]["expected_card15_fields"]
        for center, level1, level2 in zip(
                q0, self.stage["level1_card15_fields"], self.stage["level2_card15_fields"]):
            self.assertEqual(
                Decimal(level2.strip()) - Decimal(center.strip()),
                2 * (Decimal(level1.strip()) - Decimal(center.strip())),
            )

    def test_all_frozen_evidence_hashes_match(self) -> None:
        self.assertEqual(E1_INDEPENDENT.STAGE_SHA256, sha256(CONFIG))
        records = [self.stage["design"], self.stage["base_tsc_config"]]
        records.extend(self.stage["evidence"].values())
        for record in records:
            with self.subTest(path=record["path"]):
                self.assertEqual(sha256(ROOT / record["path"]), record["sha256"])

    def test_observation_contract_does_not_claim_future_or_pre_takeover_state(self) -> None:
        contract = self.stage["observation_contract"]
        self.assertTrue(contract["r_geo_z_geo_ip_exact_noiseless_before_issue"])
        self.assertTrue(contract["same_state_paired_boundary_required"])
        self.assertTrue(contract["complete_causal_history_since_takeover_available"])
        self.assertFalse(contract["pre_takeover_history_asserted_available"])
        self.assertFalse(contract["future_successor_observed_before_issue"])

    def test_post_state17_policy_forbids_every_further_plant_action(self) -> None:
        policy = self.stage["post_state17_policy"]
        self.assertTrue(policy["unconditional_stop"])
        self.assertTrue(policy["issue17_forbidden"])
        self.assertTrue(policy["state18_forbidden"])
        self.assertTrue(policy["return_or_cleanup_plant_action_forbidden"])

    def test_launcher_has_only_offline_run_and_independent_modes(self) -> None:
        launcher = (ROOT / "run_rgeo_zgeo_1ms_nr2r2c2aa4e1.sh").read_text(encoding="utf-8")
        self.assertIn('MODE="${C2AA4E1_MODE:-offline}"', launcher)
        self.assertIn("elif [ \"$MODE\" = run ]", launcher)
        self.assertIn("elif [ \"$MODE\" = independent ]", launcher)
        self.assertNotIn("resume", launcher.lower())


class C2AA4E1PureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_action_timing_separates_effect_delay_from_level2_dwell_age(self) -> None:
        target = SimpleNamespace(
            card15_fields=tuple(self.stage["level2_card15_fields"]),
            current_a_tsc=tuple(0.0 for _ in range(14)),
        )
        expected_ages = (None, None) + tuple(range(1, 16))
        for issue, expected_age in enumerate(expected_ages):
            with self.subTest(issue=issue):
                action = E1._target_action(target, issue, 0.0)
                self.assertEqual(action["issue_time_ms"], 1100 + issue)
                self.assertEqual(action["effect_state_index"], issue + 1)
                self.assertEqual(action["effect_delay_steps"], 1)
                self.assertEqual(action["level2_dwell_effect_age"], expected_age)
        self.assertEqual(E1._target_action(target, 16, 0.0)["level2_dwell_effect_age"], 15)

    def test_every_safety_or_scientific_config_mutation_fails_closed(self) -> None:
        E1._require_exact_stage(copy.deepcopy(self.stage))
        mutations = (
            (("prefix_match_tolerance", "geometry_m"), 2e-12),
            (("empirical_successor_acceptance", "r_geo_m"), 0.0021),
            (("empirical_successor_acceptance", "is_preaction_transition_bound"), True),
            (("preissue16_outer_clearance", "r_geo_m"), 0.019),
            (("preissue16_outer_clearance", "is_qualified_transition_tube"), True),
            (("inner_r_radius_m",), 0.026),
            (("outer_ip_fraction",), 0.11),
            (("model_or_expert_use",), "allowed"),
            (("qualification_use",), "allowed"),
            (("routes", "observed"), "WEAKENED_ROUTE"),
            (("schedule", 2, "level"), "q0"),
        )
        for path, value in mutations:
            changed = copy.deepcopy(self.stage)
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(E1.InputIntegrityError):
                E1._require_exact_stage(changed)

    def test_prefix_comparison_is_exact_and_fails_before_next_issue(self) -> None:
        state = {
            "time_ms": 1100,
            "r_geo_m": 0.70,
            "z_geo_m": 0.04,
            "r_mid_m": 0.71,
            "ip_a": 31_000.0,
            "actual_current_decimal_a_tsc": ["0"] * 14,
            "wire_current_a": [0.0] * 48,
            "artifact_sha256": {name: "same" for name in self.stage["semantic_artifacts"]},
        }
        reference = {"states": [copy.deepcopy(state)], "actions": []}
        self.assertEqual(
            E1.prefix_mismatch_reasons([copy.deepcopy(state)], [], reference, self.stage, 0),
            [],
        )
        cases = {
            "r_geo_m": "PREFIX_GEOMETRY:0",
            "ip_a": "PREFIX_IP:0",
            "actual_current_decimal_a_tsc": "PREFIX_COIL:0",
            "wire_current_a": "PREFIX_WIRE:0",
            "artifact_sha256": "PREFIX_SEMANTIC_ARTIFACT:0",
        }
        for key, expected in cases.items():
            changed = copy.deepcopy(state)
            if key == "actual_current_decimal_a_tsc":
                changed[key][0] = "0.1"
            elif key == "wire_current_a":
                changed[key][0] = 0.1
            elif key == "artifact_sha256":
                changed[key]["geqdsk"] = "different"
            else:
                changed[key] += 0.1
            with self.subTest(key=key):
                self.assertIn(
                    expected,
                    E1.prefix_mismatch_reasons([changed], [], reference, self.stage, 0),
                )

    def test_replay_pair_requires_exact_coil_and_wire_vector_lengths(self) -> None:
        left = json.loads(
            (ROOT / self.stage["evidence"]["a3_replay_0"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        right = json.loads(
            (ROOT / self.stage["evidence"]["a3_replay_1"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(E1._replays_equal(left, right, self.stage), (True, True))
        mutations = (
            ("wire_short", "wire_current_a", lambda values: values[:-1]),
            ("wire_long", "wire_current_a", lambda values: values + [0.0]),
            (
                "coil_short",
                "actual_current_decimal_a_tsc",
                lambda values: values[:-1],
            ),
            (
                "coil_long",
                "actual_current_decimal_a_tsc",
                lambda values: values + ["0"],
            ),
        )
        for name, key, mutate in mutations:
            changed = copy.deepcopy(right)
            changed["states"][0][key] = mutate(changed["states"][0][key])
            with self.subTest(name=name):
                self.assertEqual(
                    E1._replays_equal(left, changed, self.stage), (False, False)
                )

    def test_primary_and_independent_route_precedence_are_identical(self) -> None:
        routes = self.stage["routes"]
        cases = (
            ([], routes["observed"]),
            (["acceptance"], routes["acceptance_fail"]),
            (["novel_execution", "acceptance"], routes["novel_execution_fail"]),
            (["clearance", "novel_execution"], routes["clearance_fail"]),
            (["known_prefix", "clearance"], routes["known_prefix_fail"]),
            (["hard_safety", "known_prefix"], routes["hard_safety_fail"]),
            (["raw_reporting", "hard_safety"], routes["raw_reporting_fail"]),
        )
        for categories, expected in cases:
            with self.subTest(categories=categories):
                primary = E1._route_for_rollout(
                    self.stage,
                    {
                        "reason_categories": categories,
                        "raw_reporting_integrity_failed": "raw_reporting" in categories,
                    },
                )
                independent = E1_INDEPENDENT._expected_route(self.stage, categories)
                self.assertEqual(primary, expected)
                self.assertEqual(independent, expected)

    def test_clearance_and_acceptance_thresholds_are_inclusive(self) -> None:
        source = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=0.0, z_geo_m=0.0), ip_a=30_000.0
        )
        at_inner = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=0.025, z_geo_m=0.025), ip_a=31_500.0
        )
        reasons, metrics = E1._state16_clearance_reasons(self.stage, source, at_inner)
        self.assertEqual(reasons, [])
        self.assertEqual(metrics["remaining_to_inner"]["r_geo_m"], 0.0)

        over_inner = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=np.nextafter(0.025, np.inf), z_geo_m=0.0),
            ip_a=30_000.0,
        )
        reasons, _ = E1._state16_clearance_reasons(self.stage, source, over_inner)
        self.assertIn("STATE16_INNER_R_GEO_M", reasons)

        before = {"r_geo_m": 0.0, "z_geo_m": 0.0, "ip_a": 30_000.0}
        at_caps = {"r_geo_m": 0.002, "z_geo_m": 0.002, "ip_a": 30_100.0}
        reasons, acceptance = E1._state17_acceptance(self.stage, source, before, at_caps)
        self.assertEqual(reasons, [])
        self.assertEqual(acceptance["state16_to_state17_absolute_delta"]["ip_a"], 100.0)
        for key, next_value, expected in (
            ("r_geo_m", np.nextafter(0.002, np.inf), "STATE17_EMPIRICAL_DELTA_R_GEO_M"),
            ("z_geo_m", np.nextafter(0.002, np.inf), "STATE17_EMPIRICAL_DELTA_Z_GEO_M"),
            ("ip_a", np.nextafter(30_100.0, np.inf), "STATE17_EMPIRICAL_DELTA_IP_A"),
        ):
            changed = dict(at_caps)
            changed[key] = next_value
            with self.subTest(key=key):
                reasons, _ = E1._state17_acceptance(self.stage, source, before, changed)
                self.assertIn(expected, reasons)

    def test_outer_hard_gate_is_inclusive_and_then_fails(self) -> None:
        source = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=0.0, z_geo_m=0.0), ip_a=30_000.0
        )
        at_cap = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=0.05, z_geo_m=0.05), ip_a=33_000.0
        )
        self.assertEqual(E1._outer_reasons(self.stage, source, at_cap), [])
        outside = SimpleNamespace(
            boundary=SimpleNamespace(r_geo_m=np.nextafter(0.05, np.inf), z_geo_m=0.0),
            ip_a=30_000.0,
        )
        self.assertIn("OUTER_R", E1._outer_reasons(self.stage, source, outside))


class C2AA4E1RunnerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.cfg, self.reference, self.targets, records = fake_rollout_inputs(self.stage)
        FakeRunner.instances = []
        FakeRunner.states = [synthetic_state(record) for record in records]
        FakeRunner.fail_issue = None
        FakeRunner.fail_before_gotsc = False
        FakeRunner.abnormal_issue = None
        self.recorded_successor_times: list[int] = []

    def run_fake(self):
        def record(_cfg, state, _stage):
            row = copy.deepcopy(state["record"])
            row["reported_returncode"] = int(state.get("returncode", 0))
            row["reported_abnormal"] = bool(state.get("abnormal", False))
            row["reported_done_reason"] = str(state.get("done_reason", ""))
            row["reported_runtime_ok"] = (
                row["reported_returncode"] == 0 and not row["reported_abnormal"]
            )
            self.recorded_successor_times.append(int(row["time_ms"]))
            return row

        with (
            mock.patch.object(E1, "CountingTSCStepRunner", FakeRunner),
            mock.patch.object(E1.RGeoZGeoSignal, "from_tsc_state", side_effect=lambda state: state["signal"]),
            mock.patch.object(E1, "_record_with_sizes", side_effect=record),
        ):
            row = E1.one_rollout(self.cfg, self.stage, self.reference, self.targets)
        return row, FakeRunner.instances[-1]

    def test_exactly_seventeen_advances_then_unconditional_stop(self) -> None:
        row, runner = self.run_fake()
        self.assertTrue(row["passed"])
        self.assertEqual(
            (row["reset_calls"], row["advance_attempts"],
             row["plant_advance_gotsc_calls"], row["verified_successful_plant_advances"]),
            (1, 17, 17, 17),
        )
        self.assertEqual(len(runner.step_calls), 17)
        for actual, target in zip(runner.step_calls, self.targets):
            np.testing.assert_array_equal(actual, np.asarray(target.current_a_tsc))
        self.assertTrue(runner.cleaned)
        self.assertEqual([state["time_ms"] for state in row["states"]], list(range(1100, 1118)))
        self.assertEqual(row["actions"][16]["maximum_issued_delta_a"], 0.0)
        self.assertEqual(row["actions"][16]["effect_delay_steps"], 1)
        self.assertEqual(row["actions"][16]["level2_dwell_effect_age"], 15)
        self.assertTrue(row["unconditional_stop_after_state17"])
        self.assertFalse(row["issue17_attempted"])
        self.assertFalse(row["state18_observed"])

    def test_pre_and_post_gotsc_failures_are_counted_without_retry(self) -> None:
        for before_gotsc, expected_gotsc in ((True, 16), (False, 17)):
            with self.subTest(before_gotsc=before_gotsc):
                FakeRunner.instances = []
                FakeRunner.fail_issue = 16
                FakeRunner.fail_before_gotsc = before_gotsc
                row, runner = self.run_fake()
                self.assertEqual(row["advance_attempts"], 17)
                self.assertEqual(row["plant_advance_gotsc_calls"], expected_gotsc)
                self.assertEqual(row["verified_successful_plant_advances"], 16)
                self.assertEqual(len(runner.step_calls), 17)
                self.assertFalse(row["retry_attempted"])
                self.assertIn("novel_execution", row["reason_categories"])
                self.assertTrue(runner.cleaned)
        FakeRunner.fail_issue = None

    def test_issue16_slew_violation_is_refused_before_runner_can_clip(self) -> None:
        fields = list(self.stage["level2_card15_fields"])
        fields[0] = "-3.550E+01"
        unsafe = E1.target_from_fields(fields, self.cfg, "test.unsafe_issue16")
        targets = self.targets[:16] + (unsafe,)

        def record(_cfg, state, _stage):
            row = copy.deepcopy(state["record"])
            row["reported_returncode"] = int(state.get("returncode", 0))
            row["reported_abnormal"] = bool(state.get("abnormal", False))
            row["reported_done_reason"] = str(state.get("done_reason", ""))
            row["reported_runtime_ok"] = (
                row["reported_returncode"] == 0 and not row["reported_abnormal"]
            )
            return row

        with (
            mock.patch.object(E1, "CountingTSCStepRunner", FakeRunner),
            mock.patch.object(E1.RGeoZGeoSignal, "from_tsc_state", side_effect=lambda state: state["signal"]),
            mock.patch.object(E1, "_record_with_sizes", side_effect=record),
        ):
            row = E1.one_rollout(self.cfg, self.stage, self.reference, targets)
        runner = FakeRunner.instances[-1]
        self.assertEqual(len(runner.step_calls), 16)
        self.assertEqual(row["advance_attempts"], 16)
        self.assertEqual(row["plant_advance_gotsc_calls"], 16)
        self.assertIn("novel_execution", row["reason_categories"])

    def test_abnormal_state17_is_seen_before_route_and_never_followed_by_issue17(self) -> None:
        FakeRunner.abnormal_issue = 16
        row, runner = self.run_fake()
        self.assertIn(1117, self.recorded_successor_times)
        self.assertEqual(len(runner.step_calls), 17)
        self.assertEqual(row["advance_attempts"], 17)
        self.assertEqual(row["verified_successful_plant_advances"], 16)
        self.assertIn("novel_execution", row["reason_categories"])
        self.assertFalse(row["issue17_attempted"])
        self.assertTrue(runner.cleaned)

    def test_live_state16_prefix_mismatch_stops_before_unknown_successor(self) -> None:
        FakeRunner.states[16]["record"]["artifact_sha256"]["geqdsk"] = "mismatch"
        row, runner = self.run_fake()
        self.assertEqual(len(runner.step_calls), 16)
        self.assertEqual(row["advance_attempts"], 16)
        self.assertFalse(row["unknown_successor_attempted"])
        self.assertIn("known_prefix", row["reason_categories"])

    def test_live_wire_length_mismatch_stops_before_unknown_successor(self) -> None:
        valid_state16 = copy.deepcopy(FakeRunner.states[16])
        for name, values in (
            ("short", valid_state16["record"]["wire_current_a"][:-1]),
            ("long", valid_state16["record"]["wire_current_a"] + [0.0]),
        ):
            with self.subTest(name=name):
                FakeRunner.instances = []
                FakeRunner.states[16] = copy.deepcopy(valid_state16)
                FakeRunner.states[16]["record"]["wire_current_a"] = values
                row, runner = self.run_fake()
                self.assertEqual(len(runner.step_calls), 16)
                self.assertEqual(row["advance_attempts"], 16)
                self.assertFalse(row["unknown_successor_attempted"])
                self.assertIn("PREFIX_WIRE_LENGTH:16", row["reasons"])
                self.assertIn("known_prefix", row["reason_categories"])


class C2AA4E1ReportingAndRawTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stage = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.tmp = inside_repo_tmp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))

    def test_run_binds_schema_source_revision_and_stage_hash_into_both_results(self) -> None:
        row = {
            "rollout_id": E1.ROLLOUT_ID,
            "candidate_id": E1.ROLLOUT_ID,
            "passed": False,
            "reasons": ["synthetic"],
            "reason_categories": ["known_prefix"],
            "failed_issue_step": 0,
            "reset_calls": 1,
            "advance_attempts": 0,
            "verified_successful_plant_advances": 0,
            "plant_advances": 0,
            "raw_observed_plant_advances": 0,
            "plant_advance_gotsc_calls": 0,
            "states": [],
            "actions": [],
            "attempted_actions": [],
            "state16_clearance": None,
            "successor_acceptance": None,
            "unknown_successor_attempted": False,
            "unknown_successor_observed": False,
            "state17_recorded": False,
            "unconditional_stop_after_state17": False,
            "issue17_attempted": False,
            "state18_observed": False,
            "retry_attempted": False,
            "identity_consumed": False,
            "advance_wall_time_s": [],
            "wall_time_s": 0.0,
        }
        inventory = {
            "compact_record_count": 0,
            "existing_raw_state_indices": [],
            "continuous_raw_state_indices": [],
            "continuous_raw_state_count": 0,
            "raw_observed_plant_advances": 0,
            "noncontinuous_raw_state_indices": [],
            "required_artifact_files_for_existing_state_directories": 0,
            "required_artifact_files": 0,
            "required_artifact_bytes": 0,
            "required_artifact_inventory_sha256": hashlib.sha256(b"").hexdigest(),
            "missing_required_artifacts_for_existing_state_directories": [],
            "runtime_failure_diagnostic_directories": [],
            "runtime_failure_diagnostic_files": 0,
            "runtime_failure_diagnostic_bytes": 0,
            "runtime_failure_diagnostic_inventory_sha256": hashlib.sha256(b"").hexdigest(),
            "unexpected_rollout_directories": [],
            "state18_directory_present": False,
        }
        cfg = SimpleNamespace(run_root=None)
        output = self.tmp / "run"
        revision = "synthetic-revision"
        expected_hash = sha256(CONFIG)
        with (
            mock.patch.object(
                E1,
                "offline",
                return_value={"passed": True, "stage_config_sha256": expected_hash},
            ),
            mock.patch.object(E1, "load", return_value=(self.stage, cfg, {"a3_replay_0": {}})),
            mock.patch.object(E1, "_source", return_value={}),
            mock.patch.object(E1, "_targets", return_value=()),
            mock.patch.object(E1, "one_rollout", return_value=copy.deepcopy(row)),
            mock.patch.object(E1, "_raw_inventory", return_value=inventory),
        ):
            result = E1.run(CONFIG, revision, output)
        compact = json.loads((output / "exploration.json").read_text(encoding="utf-8"))
        for record in (compact, result):
            self.assertEqual(record["schema_version"], E1.SCHEMA)
            self.assertEqual(record["source_revision"], revision)
        self.assertEqual(compact["stage_config_sha256"], expected_hash)

    def test_raw_scan_rejects_forbidden_1118_and_extra_directories(self) -> None:
        rollout = self.tmp / "run" / "rollouts" / E1.ROLLOUT_ID
        (rollout / "1100ms").mkdir(parents=True)
        (rollout / "1118ms").mkdir()
        (rollout / "unexpected").mkdir()
        scan = E1_INDEPENDENT._scan_raw_directories(rollout, self.tmp / "run")
        self.assertTrue(scan["forbidden_1118_present"])
        self.assertIn(18, scan["actual_state_indices"])
        self.assertEqual(scan["continuous_state_indices"], [0])
        self.assertTrue(scan["unexpected_directories"])

    def test_state17_inputa_is_level2_but_is_not_an_issue17(self) -> None:
        folder = self.tmp / "1117ms"
        folder.mkdir()
        lines = [f"{'15':<10}{'':20}{field}" for field in self.stage["level2_card15_fields"]]
        (folder / "inputa").write_text("\n".join(lines) + "\n", encoding="utf-8")
        target = SimpleNamespace(card15_fields=tuple(self.stage["level2_card15_fields"]))
        self.assertEqual(E1_INDEPENDENT._state17_card15_reasons(folder, target), [])
        lines[0] = f"{'15':<10}{'':20}{'-3.500E+01'}"
        (folder / "inputa").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertTrue(E1_INDEPENDENT._state17_card15_reasons(folder, target))


class C2AA4E1PackageVerificationTests(unittest.TestCase):
    TOOL_REVISION = "1" * 40

    def setUp(self) -> None:
        self.tmp = inside_repo_tmp()
        self.addCleanup(lambda: shutil.rmtree(self.tmp, ignore_errors=True))
        self.package = self.tmp / "package"
        self.package.mkdir()
        self.manifest_sha, self.checksum_sha = build_synthetic_package(
            self.package, self.TOOL_REVISION
        )

    def test_fixed_payload_and_checksum_cardinality(self) -> None:
        self.assertEqual(len(E1_PACKAGE.EXPECTED_PAYLOAD_FILES), 39)
        self.assertEqual(len(E1_PACKAGE.EXPECTED_CHECKSUM_FILES), 40)
        self.assertEqual(E1_PACKAGE.EXPECTED_CHECKSUM_FILES[0], E1_PACKAGE.MANIFEST_PATH)
        self.assertNotIn(E1_PACKAGE.CHECKSUM_PATH, E1_PACKAGE.EXPECTED_CHECKSUM_FILES)
        self.assertEqual(len(E1_PACKAGE.TSC_PACKAGE_RUNTIME_FILES), 17)
        self.assertEqual(E1_PACKAGE.RUNTIME_REVISION, "145ab1f77c20c8a324274d39be38bbfdf3dc4009")
        self.assertEqual(E1_PACKAGE.STAGE_CONFIG_SHA256, sha256(CONFIG))

    def test_empty_direct_copy_package_verifies_with_zero_runner_calls(self) -> None:
        completed, result = run_package_verifier(
            self.package, self.manifest_sha, self.checksum_sha, self.TOOL_REVISION
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertTrue(result["passed"])
        self.assertEqual(result["payload_files_verified"], 39)
        self.assertEqual(result["checksum_entries_verified"], 40)
        self.assertEqual(result["runtime_import_files_reached"], 24)
        self.assertEqual(
            (result["reset_calls"], result["advance_attempts"],
             result["plant_advance_gotsc_calls"], result["new_tsc_or_plant_advances"]),
            (0, 0, 0, 0),
        )

    def test_external_manifest_hash_is_checked_before_manifest_parse(self) -> None:
        manifest = self.package / E1_PACKAGE.MANIFEST_PATH
        manifest.write_bytes(b"not-json\n")
        completed, result = run_package_verifier(
            self.package, self.manifest_sha, self.checksum_sha, self.TOOL_REVISION
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(result["passed"])
        self.assertIn("external manifest SHA-256 mismatch", result["failures"][0])
        self.assertNotIn("JSON", result["failures"][0])
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)

    def test_payload_mutation_fails_closed(self) -> None:
        payload = self.package / E1_PACKAGE.RUNTIME_ENTRYPOINT_FILES[0]
        payload.write_bytes(payload.read_bytes() + b"\n# mutation\n")
        completed, result = run_package_verifier(
            self.package, self.manifest_sha, self.checksum_sha, self.TOOL_REVISION
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(result["passed"])
        self.assertIn("payload size mismatch", result["failures"][0])
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)

    def test_checksum_cannot_omit_a_declared_payload(self) -> None:
        checksum_path = self.package / E1_PACKAGE.CHECKSUM_PATH
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
        checksum_path.write_text(
            "\n".join(lines[:-1]) + "\n", encoding="utf-8", newline="\n"
        )
        completed, result = run_package_verifier(
            self.package,
            self.manifest_sha,
            sha256(checksum_path),
            self.TOOL_REVISION,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(result["passed"])
        self.assertIn("checksum fileset/order", result["failures"][0])
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)

    def test_manifest_cannot_reassign_runtime_file_to_tool_revision(self) -> None:
        manifest_path = self.package / E1_PACKAGE.MANIFEST_PATH
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in manifest["files"]:
            if row["path"] == E1_PACKAGE.RUNTIME_ENTRYPOINT_FILES[0]:
                row["source_revision"] = self.TOOL_REVISION
                break
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifest_sha = sha256(manifest_path)
        checksum_path = self.package / E1_PACKAGE.CHECKSUM_PATH
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
        lines[0] = f"{manifest_sha}  {E1_PACKAGE.MANIFEST_PATH}"
        checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        completed, result = run_package_verifier(
            self.package, manifest_sha, sha256(checksum_path), self.TOOL_REVISION
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(result["passed"])
        self.assertIn("manifest source revision mismatch", result["failures"][0])
        self.assertEqual(result["new_tsc_or_plant_advances"], 0)


if __name__ == "__main__":
    unittest.main()
