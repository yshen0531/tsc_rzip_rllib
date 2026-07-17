#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage1_controllability import (
    load_and_resolve_stage1_config,
    run_analysis,
    run_scan,
    run_validation,
    synthetic_self_test,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage-1 TSC/RZIP controllability, sensitivity, and 100 ms reachability diagnostics."
    )
    parser.add_argument(
        "command",
        choices=["scan", "analyze", "validate", "all", "self-test"],
        help="pipeline phase",
    )
    parser.add_argument("--config", default="configs/stage1_controllability_100ms.json")
    parser.add_argument("--run-dir", default=None, help="existing run directory for resume/analyze/validate")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument("--no-resume", action="store_true", help="rerun completed experiments")
    args = parser.parse_args()

    if args.command == "self-test":
        print(json.dumps(synthetic_self_test(), indent=2))
        return

    resolved = load_and_resolve_stage1_config(args.config, run_dir_override=args.run_dir)
    print(f"[stage1] run_dir={resolved.paths.run_dir}", flush=True)
    resume = not args.no_resume

    if args.command in {"scan", "all"}:
        print(json.dumps(run_scan(resolved, backend=args.backend, resume=resume), indent=2), flush=True)
    if args.command in {"analyze", "all"}:
        print(json.dumps(run_analysis(resolved), indent=2), flush=True)
    if args.command in {"validate", "all"}:
        print(json.dumps(run_validation(resolved, backend=args.backend, resume=resume), indent=2), flush=True)


if __name__ == "__main__":
    main()
