#!/usr/bin/env bash
set -euo pipefail
python -u scripts/stage1_controllability.py self-test
python -u tests/test_stage1_synthetic.py
