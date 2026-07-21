#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage2_trajectory_optimization import (
    analyze_stage2,
    initialize_stage2_run,
    load_stage2_config,
    run_confirmation,
    run_one_generation,
    run_optimization,
    synthetic_stage2_test,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Stage2: optimize a 3-mode, 5-node, 100 ms control trajectory with "
            "CEM and real-TSC evaluation. The Stage1.1 linear model is used only "
            "for cheap position/Ip pre-screening."
        )
    )
    parser.add_argument(
        "command",
        choices=["prepare", "generation", "optimize", "confirm", "analyze", "all", "self-test"],
    )
    parser.add_argument("--config", default="configs/stage2_svd3_real_tsc_cem_100ms.json")
    parser.add_argument("--source-run", default=None, help="completed Stage1.1 run directory")
    parser.add_argument("--run-dir", default=None, help="Stage2 output or resume directory")
    parser.add_argument("--backend", choices=["ray", "serial"], default="ray")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    if args.command == "self-test":
        print(json.dumps(synthetic_stage2_test(), indent=2))
        return

    ctx = load_stage2_config(
        args.config,
        source_run=args.source_run,
        run_dir_override=args.run_dir,
    )
    initialize_stage2_run(ctx)
    print(f"[Stage2] source_run={ctx.source_run}", flush=True)
    print(f"[Stage2] run_dir={ctx.paths.run_dir}", flush=True)
    resume = not args.no_resume

    if args.command == "prepare":
        return
    if args.command == "generation":
        print(json.dumps(run_one_generation(ctx, backend=args.backend, resume=resume), indent=2), flush=True)
        return
    if args.command in {"optimize", "all"}:
        print(json.dumps(run_optimization(ctx, backend=args.backend, resume=resume), indent=2), flush=True)
    if args.command in {"confirm", "all"}:
        print(json.dumps(run_confirmation(ctx, backend=args.backend, resume=resume), indent=2), flush=True)
    if args.command in {"analyze", "all"}:
        print(json.dumps(analyze_stage2(ctx), indent=2), flush=True)


if __name__ == "__main__":
    main()
