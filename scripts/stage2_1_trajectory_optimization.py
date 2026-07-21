#!/usr/bin/env python3
"""CLI for Stage2.1 dual-archive real-TSC trajectory optimization."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage2_1_trajectory_optimization import execute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage2.1: warm-start from a completed Stage2 run, retain damped and "
            "precise archives independently, and locally optimize the final three nodes."
        )
    )
    parser.add_argument(
        "command",
        choices=("prepare", "generation", "optimize", "confirm", "analyze", "all", "self-test"),
    )
    parser.add_argument(
        "--config",
        default="configs/stage2_1_svd3_dual_archive_tail_cem_100ms.json",
    )
    parser.add_argument(
        "--source-run",
        dest="source_stage1_1_run",
        default=os.environ.get("SOURCE_STAGE1_1_RUN"),
        help="Completed Stage1.1 run used by the validated Stage2 loader.",
    )
    parser.add_argument(
        "--source-stage2-run",
        default=os.environ.get("SOURCE_STAGE2_RUN"),
        help="Completed Stage2 run whose real-TSC results seed Stage2.1.",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Stage2.1 output directory. If omitted, the config creates a timestamped directory.",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Require a brand-new Stage2.1 state. Omit this flag to resume completed candidate files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    execute(
        command=args.command,
        config_path=Path(args.config),
        source_stage1_1_run=args.source_stage1_1_run,
        source_stage2_run=args.source_stage2_run,
        run_dir=args.run_dir,
        backend=args.backend,
        no_resume=bool(args.no_resume),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
