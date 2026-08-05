#!/usr/bin/env python3
"""Primary zero-TSC R8R1 short-horizon discriminator."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from tsc_rzip_rllib.diagnostics import (
    stage4_2r3c3t13s24d1r14r8_partitioned_broad_response_identification as r8,
    stage4_2r3c3t13s24d1r14r8r1_fixed_candidate_short_horizon_discriminator as r8r1,
)


def _json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file(path: Path, *, size: int, sha: str, label: str) -> None:
    if not path.is_file() or path.stat().st_size != size or _sha(path) != sha:
        raise ValueError(f"R8R1 {label} contract changed")


def _source_items(
    cfg: Mapping[str, Any],
    config_path: Path,
    r8_run: Path,
    source_r2_run: Path,
    source_r4_run: Path,
    source_r6_run: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    source_config = (root / str(cfg["source_r8_config"])).resolve()
    if _sha(source_config) != str(cfg["source_r8_config_sha256"]):
        raise ValueError("R8R1 source R8 config changed")
    r8_cfg = _json(source_config)
    r8._validate_config(r8_cfg, source_config)
    contract = cfg["source_r8_contract"]
    paths = r8._paths(r8_run)
    _file(paths.state, size=int(contract["stage_state_bytes"]), sha=str(contract["stage_state_sha256"]), label="state")
    _file(paths.manifest, size=int(contract["stage_manifest_bytes"]), sha=str(contract["stage_manifest_sha256"]), label="manifest")
    primary_detailed = paths.analysis / "training_model_primary_detailed.json"
    primary_summary = paths.analysis / "training_model_primary_summary.json"
    independent = paths.analysis / "training_model_independent.json"
    if _sha(primary_detailed) != str(contract["primary_detailed_sha256"]):
        raise ValueError("R8R1 source primary detailed result changed")
    if _sha(primary_summary) != str(contract["primary_summary_sha256"]):
        raise ValueError("R8R1 source primary summary changed")
    _file(
        independent,
        size=int(contract["independent_model_bytes"]),
        sha=str(contract["independent_model_sha256"]),
        label="independent model audit",
    )
    state, summary, independent_value = _json(paths.state), _json(primary_summary), _json(independent)
    if (
        state.get("phase_status") != contract["required_phase_status"]
        or int(state.get("new_raw_count", -1)) != int(contract["required_new_raw_count"])
        or bool(state.get("heldout_outcomes_opened"))
        or state.get("training_model_sha256") != contract["required_training_model_sha256"]
        or state.get("calibrated_tube_sha256") != contract["required_calibrated_tube_sha256"]
        or (state.get("verdict") or {}).get("route") != contract["required_route"]
        or summary.get("route") != contract["required_route"]
        or summary.get("passed") is not False
        or independent_value.get("passed") is not True
        or independent_value.get("scientific_gate_passed") is not False
        or independent_value.get("primary_numerical_agreement") is not True
        or independent_value.get("primary_outcome_agreement") is not True
        or independent_value.get("model_artifact_presence_agreement") is not True
        or independent_value.get("training_model_sha256") != ""
    ):
        raise ValueError("R8R1 source R8 terminal outcome changed")
    inventory = r8._inventory(paths.phase_raw("training"))
    if (
        inventory["count"] != int(contract["training_raw_count"])
        or inventory["bytes"] != int(contract["training_raw_bytes"])
        or inventory["digest"] != str(contract["training_raw_digest"])
    ):
        raise ValueError("R8R1 source training raw inventory changed")
    if any(paths.phase_raw("calibration").glob("*.json.gz")) or any(paths.phase_raw("holdout").glob("*.json.gz")):
        raise ValueError("R8R1 source R8 held-out outcomes were opened")
    ctx = r8.Context(
        cfg=r8_cfg,
        config_path=source_config,
        d1r11_ctx=None,
        source_d1r11_run=r8_run,
        source_response_runs={
            "r2": source_r2_run.resolve(),
            "r4": source_r4_run.resolve(),
            "r6": source_r6_run.resolve(),
        },
        paths=paths,
    )
    existing, existing_bank = r8._existing_training_items(ctx)
    extension, extension_bank = r8.build_new_items(ctx, "training")
    items = sorted(existing + extension, key=lambda row: str(row["response_id"]))
    detailed = _json(primary_detailed)
    if (
        len(items) != int(cfg["bank_contract"]["response_count"])
        or len({str(row["pair_id"]) for row in items}) != int(cfg["bank_contract"]["pair_count"])
        or len({str(row["context_id"]) for row in items}) != int(cfg["bank_contract"]["context_count"])
        or existing_bank != detailed["existing_bank"]
        or extension_bank != detailed["extension_bank"]
        or any(len(row["descriptor"]) != int(cfg["bank_contract"]["descriptor_dimension"]) for row in items)
        or any(len(row["response"]) < int(cfg["horizon_contract"]["minimum_response_length"]) for row in items)
    ):
        raise ValueError("R8R1 reconstructed training bank changed")
    authentication = {
        "source_r8_run": str(r8_run),
        "source_state_sha256": _sha(paths.state),
        "source_manifest_sha256": _sha(paths.manifest),
        "source_training_inventory": {key: inventory[key] for key in ("count", "bytes", "digest")},
        "source_primary_detailed_sha256": _sha(primary_detailed),
        "source_primary_summary_sha256": _sha(primary_summary),
        "source_independent_sha256": _sha(independent),
        "calibration_raw_count": 0,
        "holdout_raw_count": 0,
        "existing_bank": existing_bank,
        "extension_bank": extension_bank,
        "combined_response_count": len(items),
        "combined_pair_count": len({str(row["pair_id"]) for row in items}),
        "combined_context_count": len({str(row["context_id"]) for row in items}),
        "passed": True,
    }
    return items, r8_cfg, authentication, detailed


def run(args: argparse.Namespace) -> dict[str, Any]:
    config_path = args.config.resolve()
    cfg = _json(config_path)
    r8r1.validate_config(cfg)
    root = Path(__file__).resolve().parents[1]
    design = (root / str(cfg["design_document"])).resolve()
    if _sha(design) != str(cfg["design_document_sha256"]):
        raise ValueError("R8R1 design hash changed")
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("R8R1 primary output directory must be empty")
    output.mkdir(parents=True, exist_ok=True)
    items, r8_cfg, authentication, source_detailed = _source_items(
        cfg, config_path, args.r8_run.resolve(), args.source_r2_run.resolve(),
        args.source_r4_run.resolve(), args.source_r6_run.resolve(),
    )
    rows, folds = r8r1.outer_prediction_rows(items, cfg, r8_cfg)
    horizons = {
        horizon: r8r1.evaluate_horizon(items, rows[horizon], horizon, cfg, r8_cfg)
        for horizon in map(int, cfg["horizon_contract"]["evaluated_relative_lags"])
    }
    selected = r8r1.select_horizon(horizons, cfg)
    route = r8r1.route_for(selected, cfg)
    model_path = output / "selected_short_horizon_model.json"
    model_sha = ""
    if selected is not None:
        _write(model_path, r8r1.fit_all_data_artifact(items, selected, cfg, r8_cfg))
        model_sha = _sha(model_path)
    detailed = {
        "schema_version": 1,
        "stage": r8r1.STAGE,
        "campaign_identity": r8r1.IDENTITY,
        "audit_kind": "primary",
        "source_authentication": authentication,
        "fixed_candidate": dict(cfg["fixed_candidate"]),
        "outer_folds": folds,
        "horizons": {str(key): value for key, value in horizons.items()},
        "selected_relative_lag_horizon": selected,
        "route": route,
        "scientific_gate_passed": selected is not None,
        "model_sha256": model_sha,
        "forbidden_predictor_input_count": 0,
        "new_raw_count": 0,
        "ray_executed": False,
        "gotsc_executed": False,
        "tsc_executed": False,
        "plant_advance_count": 0,
        "probe_trajectories_allowed_in_expert_dataset": False,
        "mpc_validated": False,
        "bc_dagger_or_rl_allowed": False,
        "passed": True,
    }
    detailed_path = output / "primary_detailed.json"
    _write(detailed_path, detailed)
    compact = {
        key: value for key, value in detailed.items() if key not in {"horizons", "outer_folds"}
    }
    compact["outer_folds"] = folds
    compact["horizons"] = {str(key): r8r1.compact_horizon(value) for key, value in horizons.items()}
    compact["primary_detailed_sha256"] = _sha(detailed_path)
    compact["source_r8_full_horizon_reproduction_reference"] = {
        "response_pass_count": source_detailed["aggregate"]["response_pass_count"],
        "maximum_relative_l2_error": source_detailed["aggregate"]["maximum_relative_l2_error"],
        "minimum_response_cosine": source_detailed["aggregate"]["minimum_response_cosine"],
    }
    _write(output / "primary_summary.json", compact)
    _write(
        output / "stage_state.json",
        {
            "schema_version": 1,
            "stage": r8r1.STAGE,
            "finished": True,
            "primary_completed": True,
            "independent_completed": False,
            "scientific_gate_passed": selected is not None,
            "selected_relative_lag_horizon": selected,
            "route": route,
            "model_sha256": model_sha,
            "new_raw_count": 0,
            "heldout_outcomes_opened": False,
        },
    )
    print(json.dumps(compact, indent=2, sort_keys=True, allow_nan=False))
    return compact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--r8-run", type=Path, required=True)
    parser.add_argument("--source-r2-run", type=Path, required=True)
    parser.add_argument("--source-r4-run", type=Path, required=True)
    parser.add_argument("--source-r6-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


if __name__ == "__main__":
    run(_parser().parse_args())
