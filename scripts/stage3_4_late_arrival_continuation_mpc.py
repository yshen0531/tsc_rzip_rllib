#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tsc_rzip_rllib.diagnostics.stage3_4_late_arrival_continuation_mpc import main
if __name__ == "__main__":
    main()
