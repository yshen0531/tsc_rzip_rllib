#!/usr/bin/env python3
"""CLI for Stage2.2 strict-corner real-TSC trajectory optimization."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage2_2_trajectory_optimization import execute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage2.2: merge complete Stage2 and Stage2.1 real-TSC histories, "
            "then locally minimize the largest strict position/speed/Ip violation."
        )
    )
    parser.add_argument(
        "command",
        choices=("prepare", "generation", "optimize", "confirm", "analyze", "all", "self-test"),
    )
    parser.add_argument(
        "--config",
        default="configs/stage2_2_svd3_corner_feasibility_100ms.json",
    )
    parser.add_argument(
        "--source-run",
        dest="source_stage1_1_run",
        default=os.environ.get("SOURCE_STAGE1_1_RUN"),
        help="Completed Stage1.1 run. Usually recovered automatically from Stage2.1.",
    )
    parser.add_argument(
        "--source-stage2-run",
        default=os.environ.get("SOURCE_STAGE2_RUN"),
        help="Completed Stage2 run. Usually recovered automatically from Stage2.1.",
    )
    parser.add_argument(
        "--source-stage2-1-run",
        default=os.environ.get("SOURCE_STAGE2_1_RUN"),
        help="Completed Stage2.1 run whose 1536 trajectories are merged with Stage2.",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Stage2.2 output directory. If omitted, config creates a timestamped directory.",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Require a brand-new Stage2.2 state. Omit to resume completed candidate files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    execute(
        command=args.command,
        config_path=args.config,
        source_stage1_1_run=args.source_stage1_1_run,
        source_stage2_run=args.source_stage2_run,
        source_stage2_1_run=args.source_stage2_1_run,
        run_dir=args.run_dir,
        backend=args.backend,
        no_resume=args.no_resume,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
