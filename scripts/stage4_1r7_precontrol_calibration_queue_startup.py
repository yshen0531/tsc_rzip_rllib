#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from tsc_rzip_rllib.diagnostics.stage4_1r7_precontrol_calibration_queue_startup import main


if __name__ == "__main__":
    main()
