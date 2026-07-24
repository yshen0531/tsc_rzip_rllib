#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from tsc_rzip_rllib.diagnostics.stage3_3_target_conditioned_mpc import main


if __name__ == "__main__":
    main()
