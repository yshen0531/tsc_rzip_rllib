#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage1_controllability import load_and_resolve_stage1_config
from tsc_rzip_rllib.diagnostics.stage1_1_supplement import (
    prepare_stage1_1_run,
    retry_failed_scan,
    run_stage1_1_analysis,
    run_stage1_1_validation,
    synthetic_stage1_1_test,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage1.1: retry failed identification runs and validate SVD2/SVD3/SVD4 with strict hold gates."
    )
    parser.add_argument(
        "command",
        choices=["prepare", "retry", "analyze", "validate", "all", "self-test"],
    )
    parser.add_argument("--config", default="configs/stage1_1_supplement_100ms.json")
    parser.add_argument("--source-run", default=None, help="completed Stage1 run directory")
    parser.add_argument("--run-dir", default=None, help="Stage1.1 output or resume directory")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--allow-incomplete-scan", action="store_true")
    args = parser.parse_args()

    if args.command == "self-test":
        print(json.dumps(synthetic_stage1_1_test(), indent=2))
        return

    resolved = load_and_resolve_stage1_config(args.config, run_dir_override=args.run_dir)
    source = prepare_stage1_1_run(resolved, source_run=args.source_run)
    print(f"[Stage1.1] source_run={source}", flush=True)
    print(f"[Stage1.1] run_dir={resolved.paths.run_dir}", flush=True)
    resume = not args.no_resume

    if args.command == "prepare":
        return
    if args.command in {"retry", "all"}:
        print(
            json.dumps(
                retry_failed_scan(resolved, allow_incomplete=args.allow_incomplete_scan),
                indent=2,
            ),
            flush=True,
        )
    if args.command in {"analyze", "all"}:
        print(json.dumps(run_stage1_1_analysis(resolved), indent=2), flush=True)
    if args.command in {"validate", "all"}:
        print(
            json.dumps(
                run_stage1_1_validation(resolved, backend=args.backend, resume=resume),
                indent=2,
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
