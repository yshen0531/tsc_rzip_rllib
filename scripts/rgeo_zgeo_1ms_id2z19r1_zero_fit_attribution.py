from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id2z19r1_20260820_4317cd2f_v2/independent_audit.json"
LEDGER = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id2z19r1_20260820_4317cd2f_v2/oof_predictions.json"
RESULT = ROOT / "docs/codex/audits/rgeo_zgeo_1ms_id2z19r1_20260820_4317cd2f_v2/result.json"
EXPECTED = {
    AUDIT: "a977d36ea4b40b32a585e3161ca04c98efeb825ae7e4505b8452aecfbd79ca5e",
    LEDGER: "234e8826b93168f474c237e5a5fcf0e323083c2e311ece90124abaefb7e7358e",
    RESULT: "2f7c0acbec9438153b9481794be45a034d347d8a39a4cb76493983c4e498a214",
}
QUALIFICATION_HORIZONS = {1, 2, 4, 8}
TERMINAL_R_CAP_M = 0.0005
MINIMUM_DIRECTION_SIGNAL_M = 0.00002
ROUTE = (
    "ONE_MS_ID2Z19R1_ATTRIBUTION_COMMON_TERMINAL_INCREMENT_MODEL_CLASS_FAIL_"
    "AUTHORITY_AXIS_AND_TARGETED_REDESIGN_REQUIRED"
)


class IntegrityError(RuntimeError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise IntegrityError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / denominator if denominator > 1.0e-30 else math.nan


def compute() -> dict[str, Any]:
    for path, expected in EXPECTED.items():
        if not path.is_file() or sha256(path) != expected:
            raise IntegrityError(f"source identity mismatch: {path}")
    result = read_json(RESULT)
    audit = read_json(AUDIT)
    ledger = read_json(LEDGER)
    if result.get("route") != "ONE_MS_ID2Z19R1_NO_ELIGIBLE_DEVELOPMENT_MODEL_ONE_ATTRIBUTION_ONLY":
        raise IntegrityError("unexpected ID2Z19R1 route")
    if result.get("passed") is not False or result["comparison"].get("selected_candidate_id") is not None:
        raise IntegrityError("unexpected ID2Z19R1 selection")
    if not audit.get("audit_passed") or audit.get("recomputed_passed") is not False:
        raise IntegrityError("independent audit mismatch")
    rows = ledger.get("rows", [])
    if len(rows) != 9408 or result.get("oof_prediction_row_count") != 9408:
        raise IntegrityError("OOF row count mismatch")

    candidate_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        candidate_rows[str(row["candidate_id"])].append(row)

    candidates = []
    result_candidates = {row["candidate_id"]: row for row in result["comparison"]["candidate_results"]}
    for candidate_id in (
        "structured_rank4_stable_memory",
        "structured_rank4_stable_memory_plus_tcn4",
    ):
        candidate = result_candidates[candidate_id]
        failure_counts = Counter(reason for fold in candidate["folds"] for reason in fold["failures"])
        support_pass_folds = sum(
            fold["metrics"]["support_coverage_fraction"] >= 0.9 for fold in candidate["folds"]
        )
        above_cap = []
        endpoint_counts: Counter[int] = Counter()
        for row in candidate_rows[candidate_id]:
            if int(row["horizon_ms"]) not in QUALIFICATION_HORIZONS:
                continue
            error = abs(
                float(row["predicted_terminal_increment"][0])
                - float(row["truth_terminal_increment"][0])
            )
            if error > TERMINAL_R_CAP_M:
                endpoint = int(row["origin_issue"]) + int(row["horizon_ms"])
                endpoint_counts[endpoint] += 1
                above_cap.append(
                    {
                        "fold_id": row["fold_id"],
                        "family_id": row["family_id"],
                        "origin_issue": row["origin_issue"],
                        "horizon_ms": row["horizon_ms"],
                        "endpoint_issue": endpoint,
                        "absolute_r_terminal_increment_error_mm": 1000.0 * error,
                        "supported": row["supported"],
                    }
                )

        pair_cells: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in candidate_rows[candidate_id]:
            if row.get("pair_id") is None or int(row["horizon_ms"]) not in QUALIFICATION_HORIZONS:
                continue
            pair_cells[(str(row["pair_id"]), int(row["origin_issue"]), int(row["horizon_ms"]))][
                str(row["sign"])
            ] = row
        negative = []
        for (pair_id, origin, horizon), pair in sorted(pair_cells.items()):
            if set(pair) != {"plus", "minus"}:
                raise IntegrityError(f"incomplete pair cell: {pair_id}/{origin}/{horizon}")
            plus, minus = pair["plus"], pair["minus"]
            truth = [float(plus["truth_state"][i]) - float(minus["truth_state"][i]) for i in (0, 1)]
            predicted = [
                float(plus["predicted_state"][i]) - float(minus["predicted_state"][i]) for i in (0, 1)
            ]
            if math.hypot(*truth) < MINIMUM_DIRECTION_SIGNAL_M:
                continue
            value = _cosine(truth, predicted)
            if value < 0.0:
                negative.append(
                    {
                        "pair_id": pair_id,
                        "origin_issue": origin,
                        "horizon_ms": horizon,
                        "endpoint_issue": origin + horizon,
                        "direction_cosine": value,
                    }
                )
        above_cap.sort(key=lambda row: row["absolute_r_terminal_increment_error_mm"], reverse=True)
        candidates.append(
            {
                "candidate_id": candidate_id,
                "eligible": candidate["eligible"],
                "failure_counts": dict(sorted(failure_counts.items())),
                "support_pass_fold_count": support_pass_folds,
                "support_fail_fold_count": 8 - support_pass_folds,
                "terminal_r_above_cap_row_count": len(above_cap),
                "terminal_r_above_cap_endpoint_counts": {
                    str(key): endpoint_counts[key] for key in sorted(endpoint_counts)
                },
                "largest_terminal_r_errors": above_cap[:20],
                "negative_direction_cell_count": len(negative),
                "negative_direction_cells": negative,
                "summary": candidate["summary"],
            }
        )

    selection = result["comparison"]["selection_diagnostics"]
    classification = bool(
        result["comparison"]["eligible_candidate_count"] == 0
        and all(row["failure_counts"].get("TERMINAL_VELOCITY") == 8 for row in candidates)
        and all(row["failure_counts"].get("TERMINAL_INCREMENT_P95") == 8 for row in candidates)
        and all(row["support_pass_fold_count"] >= 7 for row in candidates)
        and selection["tcn_relative_selection_gate_passed"] is False
    )
    return {
        "schema_version": "rgeo-zgeo-1ms-id2z19r1-zero-fit-attribution-v1",
        "passed": classification,
        "route": ROUTE if classification else "ONE_MS_ID2Z19R1_ATTRIBUTION_INTEGRITY_OR_CLASSIFICATION_STOP",
        "source_hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): digest for path, digest in EXPECTED.items()},
        "oof_prediction_row_count": len(rows),
        "candidate_attribution": candidates,
        "selection_diagnostics": selection,
        "calibration_records_read": 0,
        "blind_holdout_records_read": 0,
        "models_fit_or_updated": 0,
        "new_tsc_calls": 0,
        "claim_boundary": (
            "Zero-fit attribution of the frozen ID2Z19R1 development OOF ledger only; "
            "not a model, calibration, holdout, authority, recovery, controller or plant result."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise IntegrityError("refusing to overwrite attribution output")
    value = compute()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

