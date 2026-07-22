#!/usr/bin/env python3
"""CLI for Stage3.0 extended-horizon real-TSC tail SQP."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tsc_rzip_rllib.diagnostics.stage3_0_tail_sqp import execute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Stage3.0: extend validated Stage2.2 trajectories to 150 ms, screen deterministic tails, "
            "then use real-TSC finite-difference trust-region SQP on six independent tail controls."
        )
    )
    parser.add_argument(
        "command",
        choices=("prepare", "screen", "round", "optimize", "identify", "confirm", "analyze", "all", "self-test"),
    )
    parser.add_argument(
        "--config",
        default="configs/stage3_0_svd3_tail_sqp_150ms.json",
    )
    parser.add_argument(
        "--source-stage2-2-run",
        default=os.environ.get("SOURCE_STAGE2_2_RUN"),
        help="Completed Stage2.2 run used for validated 100 ms nominals and the three SVD modes.",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Stage3.0 output directory. If omitted, the config creates a timestamped run directory.",
    )
    parser.add_argument("--backend", choices=("ray", "serial"), default="ray")
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Require a brand-new Stage3.0 state. Omit to reuse completed candidate JSON files.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    execute(
        command=args.command,
        config_path=args.config,
        source_stage2_2_run=args.source_stage2_2_run,
        run_dir=args.run_dir,
        backend=args.backend,
        no_resume=args.no_resume,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
