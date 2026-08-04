#!/usr/bin/env python3
"""Primary zero-TSC causal deconfounded response-model audit for D1R14R7."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from tsc_rzip_rllib.control import causal_response_model as crm


STAGE = "Stage4.2R3c3T13S24D1R14R7"
IDENTITY = "causal_deconfounded_response_model_development_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("R7 raw root is not an object")
    return value


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _inventory(directory: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    rows = []
    for path in sorted(directory.glob("*.json.gz")):
        size = path.stat().st_size
        sha = _sha256(path)
        digest.update(f"{path.name}\0{size}\0{sha}\n".encode())
        rows.append({"name": path.name, "size": size, "sha256": sha})
    return {
        "count": len(rows),
        "bytes": sum(int(row["size"]) for row in rows),
        "digest": digest.hexdigest(),
        "rows": rows,
    }


def _validate_config(cfg: Mapping[str, Any]) -> None:
    bank = cfg["bank_contract"]
    model = cfg["model_contract"]
    gates = cfg["gates"]
    execution = cfg["execution_contract"]
    timing = cfg["formal_timing_contract"]
    scope = cfg["scientific_scope"]
    invalid = (
        cfg.get("stage") != STAGE
        or cfg.get("identity") != IDENTITY
        or cfg.get("package_revision") != "r42r3c3t13s24d1r14r7_causal_response_model_v1"
        or cfg.get("design_document_sha256") != "567a02c6ce4f8e52c2d517f2eca1ceef52314796b051f5ab43a5b92144337897"
        or tuple(map(int, bank["issue_task_steps"])) != (10, 14, 18, 22)
        or tuple(map(int, bank["descriptor_state_offsets"])) != (0, 1, 2, 4, 8)
        or tuple(map(float, bank["response_scales"])) != (0.03, 0.03, 0.1, 0.1, 10000.0)
        or tuple(map(float, bank["target_scales"])) != (0.03, 0.03, 10000.0)
        or tuple(int(bank[key]) for key in ("context_count", "pair_count", "histories_per_pair", "direction_count", "response_count")) != (8, 4, 2, 4, 256)
        or tuple(map(int, model["pca_ranks"])) != (2, 4, 6)
        or tuple(map(float, model["rbf_median_distance_multipliers"])) != (0.5, 1.0, 2.0)
        or tuple(map(float, model["kernel_ridges"])) != (1e-6, 1e-3, 1e-1)
        or not bool(model["nested_whole_pair_selection"])
        or bool(model["final_all_data_fit_is_validation"])
        or tuple(float(gates[key]) for key in ("maximum_relative_l2_error", "minimum_response_cosine", "minimum_peak_ratio", "maximum_peak_ratio", "maximum_absolute_scaled_point_error", "minimum_predicted_peak", "maximum_condition_number")) != (0.75, 0.8, 0.5, 1.5, 0.1, 0.0025, 20.0)
        or tuple(map(float, gates["tube_caps_physical"])) != (0.003, 0.003, 0.01, 0.01, 1000.0)
        or tuple(int(timing[key]) for key in ("normal_arrival_deadline_step", "normal_hold_through_step", "weak_arrival_deadline_step", "weak_hold_through_step")) != (25, 35, 27, 37)
        or bool(timing["arrival_deadline_expansion_allowed"])
        or bool(timing["evaluated_in_r7"])
        or int(execution["new_raw_count"]) != 0
        or int(execution["plant_steps_executed"]) != 0
        or any(bool(execution[key]) for key in ("controller_executed", "ray_executed", "gotsc_executed", "tsc_executed"))
        or not bool(execution["source_raw_read_in_place"])
        or not bool(scope["identification_development_only"])
        or any(bool(scope[key]) for key in ("probe_trajectories_allowed_in_expert_dataset", "transition_response_model_validated_fresh", "mpc_validated", "expert_data_allowed", "bc_dagger_or_rl_allowed"))
        or len(crm.candidates(cfg)) != 27
    )
    if invalid:
        raise ValueError("D1R14R7 frozen configuration changed")


def _source_paths(run: Path, contract: Mapping[str, Any]) -> dict[str, Path]:
    if run.name != str(contract["run_name"]):
        raise ValueError("R7 source run identity changed")
    stage = run / str(contract["stage_directory"])
    return {
        "stage": stage,
        "raw": stage / "raw",
        "specs": stage / "specs" / "sentinel_specs.json",
        "final": stage / "analysis" / "final_result.json",
        "independent": run / "server_independent_forensics_v1.json",
    }


def _authenticate_source(run: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    paths = _source_paths(run, contract)
    inventory = _inventory(paths["raw"])
    if (
        inventory["count"] != int(contract["raw_count"])
        or inventory["bytes"] != int(contract["raw_bytes"])
        or inventory["digest"] != str(contract["raw_digest"])
        or _sha256(paths["final"]) != str(contract["final_sha256"])
        or _sha256(paths["independent"]) != str(contract["independent_sha256"])
    ):
        raise ValueError("R7 source inventory or result hash changed")
    final = _json(paths["final"])
    independent = _json(paths["independent"])
    if final.get("route") != contract["required_route"] or independent.get("route") != contract["required_route"]:
        raise ValueError("R7 source route changed")
    specs = _json(paths["specs"])
    if len(specs) != int(contract["raw_count"]):
        raise ValueError("R7 source spec count changed")
    results = {}
    expected = {row["name"]: row for row in inventory["rows"]}
    for spec in specs:
        experiment_id = str(spec["experiment_id"])
        path = paths["raw"] / f"{experiment_id}.json.gz"
        row = expected.get(path.name)
        if row is None or path.stat().st_size != int(row["size"]) or _sha256(path) != row["sha256"]:
            raise ValueError("R7 source raw row changed")
        result = _gzip(path)
        if result.get("experiment_id") != experiment_id or result.get("spec") != spec or result.get("completed") is not True or result.get("success") is not True:
            raise ValueError("R7 source raw identity or completion changed")
        results[experiment_id] = result
    return {"paths": paths, "inventory": inventory, "specs": specs, "results": results, "final": final, "independent": independent}


def _visible(trajectory: Sequence[Mapping[str, Any]], scales: np.ndarray) -> np.ndarray:
    rows = []
    for index, state in enumerate(trajectory):
        if index == 0:
            other = trajectory[1]
            v_r = (float(other["R"]) - float(state["R"])) / 0.01
            v_z = (float(other["Z"]) - float(state["Z"])) / 0.01
        else:
            previous = trajectory[index - 1]
            v_r = (float(state["R"]) - float(previous["R"])) / 0.01
            v_z = (float(state["Z"]) - float(previous["Z"])) / 0.01
        rows.append([float(state["R"]), float(state["Z"]), v_r, v_z, float(state["Ip"])])
    value = np.asarray(rows, dtype=float) / scales
    if not np.all(np.isfinite(value)):
        raise ValueError("R7 visible trajectory is non-finite")
    return value


def _groups(source: Mapping[str, Any], prefix: str, default_issue: int) -> dict[str, dict[tuple[str, int, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]]:
    output: dict[str, dict[tuple[str, int, int, int], tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for spec in source["specs"]:
        role = str(spec[f"{prefix}_role"])
        issue = int(spec.get(f"{prefix}_issue_task_step", default_issue)) if role == "signed_probe" else -1
        key = (role, issue, int(spec[f"{prefix}_direction_index"]), int(spec[f"{prefix}_sign"]))
        context = str(spec["source_d1r13_experiment_id"])
        if key in output.setdefault(context, {}):
            raise ValueError("R7 duplicate source bank member")
        output[context][key] = (spec, source["results"][str(spec["experiment_id"])])
    return output


def build_items(sources: Mapping[str, Mapping[str, Any]], cfg: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scales = np.asarray(cfg["bank_contract"]["response_scales"], dtype=float)
    target_scales = np.asarray(cfg["bank_contract"]["target_scales"], dtype=float)
    offsets = tuple(map(int, cfg["bank_contract"]["descriptor_state_offsets"]))
    r2 = _groups(sources["r2"], "d1r14r2", 10)
    r4 = _groups(sources["r4"], "d1r14r4", -1)
    r6 = _groups(sources["r6"], "d1r14r6", -1)
    contexts = sorted(r2)
    if contexts != sorted(r4) or contexts != sorted(r6) or len(contexts) != 8:
        raise ValueError("R7 context closure changed")
    items = []
    for context in contexts:
        for issue in (10, 14, 18, 22):
            baseline_group = r2[context] if issue == 10 else r4[context]
            baseline_spec, baseline_result = baseline_group[("baseline", -1, -1, 0)]
            baseline_visible = _visible(baseline_result["trajectory"], scales)
            state_indices = [max(0, issue - offset) for offset in offsets]
            target = np.asarray([
                float(baseline_spec["target_R_offset_m"]),
                float(baseline_spec["target_Z_offset_m"]),
                float(baseline_spec["target_Ip_offset_A"]),
            ]) / target_scales
            descriptor = np.concatenate((baseline_visible[state_indices].reshape(-1), target, [(issue - 10.0) / 12.0]))
            for sign in (-1, 1):
                for direction in range(4):
                    if issue == 10:
                        spec, result = r2[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R2"
                    elif direction == 0:
                        spec, result = r6[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R6"
                    else:
                        spec, result = r4[context][("signed_probe", issue, direction, sign)]
                        source_stage = "R4"
                    member = _visible(result["trajectory"], scales)[issue + 1 :]
                    baseline = baseline_visible[issue + 1 :]
                    if member.shape != baseline.shape:
                        raise ValueError("R7 matched response shape changed")
                    response = member - baseline
                    items.append({
                        "response_id": str(spec["experiment_id"]),
                        "source_stage": source_stage,
                        "context_id": context,
                        "pair_id": str(spec["pair_id"]),
                        "history_member": str(spec["history_member"]),
                        "issue_task_step": issue,
                        "sign": sign,
                        "direction_index": direction,
                        "descriptor": descriptor.tolist(),
                        "response": response.tolist(),
                    })
    pairs = sorted({str(item["pair_id"]) for item in items})
    histories = {pair: sorted({str(item["history_member"]) for item in items if item["pair_id"] == pair}) for pair in pairs}
    signature = {
        "response_count": len(items), "context_count": len(contexts), "pair_count": len(pairs),
        "pairs": pairs, "histories_by_pair": histories,
        "source_counts": {name: sum(item["source_stage"] == name for item in items) for name in ("R2", "R4", "R6")},
        "bank_digest": crm.canonical_digest([
            {key: item[key] for key in ("response_id", "source_stage", "context_id", "pair_id", "history_member", "issue_task_step", "sign", "direction_index", "descriptor", "response")}
            for item in sorted(items, key=lambda row: row["response_id"])
        ]),
    }
    if len(items) != 256 or len(pairs) != 4 or any(value != ["minus_first", "plus_first"] for value in histories.values()) or signature["source_counts"] != {"R2": 64, "R4": 144, "R6": 48}:
        raise ValueError("R7 response bank contract changed")
    return sorted(items, key=lambda row: row["response_id"]), signature


def run(args: argparse.Namespace) -> dict[str, Any]:
    project = args.project.resolve()
    cfg = _json(args.config.resolve())
    _validate_config(cfg)
    if _sha256(args.design_document.resolve()) != cfg["design_document_sha256"]:
        raise ValueError("R7 design-document hash changed")
    if args.output.exists():
        raise ValueError("R7 output directory must be new")
    runs = {"r2": args.source_r2_run.resolve(), "r4": args.source_r4_run.resolve(), "r6": args.source_r6_run.resolve()}
    sources = {name: _authenticate_source(path, cfg["source_contracts"][name]) for name, path in runs.items()}
    items, bank = build_items(sources, cfg)
    rows, folds = crm.nested_outer_rows(items, cfg)
    aggregate = crm.aggregate(rows, cfg)
    predicted_geometry = crm.geometry(rows, cfg)
    passed = bool(aggregate["passed"] and predicted_geometry["passed"])
    final_candidate, final_scores = crm.select_candidate(items, cfg)
    model_artifact = None
    model_digest = None
    if passed:
        model_artifact = crm.serializable_model(crm.fit_model(items, final_candidate, cfg))
        model_digest = crm.canonical_digest(model_artifact)
    route = cfg["routes"]["pass" if passed else "model_fail"]
    detailed = {
        "schema_version": 1, "stage": STAGE, "identity": IDENTITY,
        "passed": passed, "route": route, "source_authentication_passed": True,
        "source_inventories": {name: value["inventory"] for name, value in sources.items()},
        "bank": bank, "nested_outer_folds": folds, "outer_prediction_rows": rows,
        "aggregate": aggregate, "predicted_geometry": predicted_geometry,
        "final_candidate_development_only": final_candidate.as_dict(),
        "final_candidate_scores": final_scores,
        "final_model_digest": model_digest,
        "execution": {"new_raw_count": 0, "plant_steps_executed": 0, "controller_executed": False, "ray_executed": False, "gotsc_executed": False, "tsc_executed": False},
        "scientific_scope": cfg["scientific_scope"],
    }
    summary = {
        "schema_version": 1, "stage": STAGE, "passed": passed, "route": route,
        "bank": bank, "aggregate": aggregate,
        "predicted_geometry": {key: value for key, value in predicted_geometry.items() if key != "rows"},
        "outer_selected_candidates": [{"held_pair_id": row["held_pair_id"], "selected_candidate": row["selected_candidate"]} for row in folds],
        "final_candidate_development_only": final_candidate.as_dict(), "final_model_digest": model_digest,
        "new_raw_count": 0, "tsc_executed": False,
    }
    args.output.mkdir(parents=True)
    detailed_path = args.output / "stage4_2r3c3t13s24d1r14r7_detailed_v1.json"
    summary_path = args.output / "stage4_2r3c3t13s24d1r14r7_summary_v1.json"
    _write(detailed_path, detailed)
    _write(summary_path, summary)
    if model_artifact is not None:
        _write(args.output / "stage4_2r3c3t13s24d1r14r7_model_v1.json", model_artifact)
    manifest = {
        "schema_version": 1, "stage": STAGE, "package_revision": cfg["package_revision"],
        "config_sha256": _sha256(args.config.resolve()), "design_document_sha256": _sha256(args.design_document.resolve()),
        "detailed_sha256": _sha256(detailed_path), "summary_sha256": _sha256(summary_path),
        "model_sha256": _sha256(args.output / "stage4_2r3c3t13s24d1r14r7_model_v1.json") if model_artifact is not None else None,
        "source_runs": {name: str(path) for name, path in runs.items()},
    }
    _write(args.output / "stage4_2r3c3t13s24d1r14r7_manifest_v1.json", manifest)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return detailed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--design-document", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
